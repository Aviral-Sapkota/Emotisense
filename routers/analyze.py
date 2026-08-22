# routers/analyze.py
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from fer_model import fer_model          
from models import Scan, User
from notifications import check_and_send_notifications
from schemas import AnalyzeRequest, EmotionResult, ScanOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analysis"])


@router.post("/analyze", response_model=EmotionResult)
async def analyze(
    body: AnalyzeRequest,
    bg:   BackgroundTasks,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Receive a base64 JPEG from the browser, run it through YOUR trained CNN,
    return emotion percentages, save to DB, and fire push notifications if rules match.
    """
    #  1. Run YOUR model (local, free, no API call) 
    try:
        prediction = fer_model.predict(body.image)
    except FileNotFoundError as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:
        logger.error("Model prediction error: %s", exc, exc_info=True)
        raise HTTPException(500, "Model inference failed. Check server logs.")

    result = EmotionResult(**prediction)

    #  2. Save to PostgreSQL (even if no face detected) 
    scan = Scan(
        user_id         = user.id,
        primary_emotion = result.primary,
        confidence      = result.confidence,
        scores          = result.scores,
        faces_detected  = result.faces_detected,
    )
    db.add(scan)
    await db.commit()

    #  3. Push notifications run in background (non-blocking) 
    if result.faces_detected > 0:
        bg.add_task(check_and_send_notifications, user.id, result, db)

    return result


@router.get("/scans", response_model=list[ScanOut])
async def get_scans(
    limit: int         = 50,
    user:  User        = Depends(get_current_user),
    db:    AsyncSession = Depends(get_db),
):
    """Return the most recent scans for the logged-in user."""
    rows = await db.execute(
        select(Scan)
        .where(Scan.user_id == user.id)
        .order_by(Scan.created_at.desc())
        .limit(limit)
    )
    return rows.scalars().all()


@router.get("/scans/stats")
async def get_stats(
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Return aggregate statistics for the logged-in user."""
    total = await db.scalar(
        select(func.count(Scan.id)).where(Scan.user_id == user.id)
    )
    top = await db.execute(
        select(Scan.primary_emotion, func.count(Scan.primary_emotion).label("cnt"))
        .where(Scan.user_id == user.id)
        .group_by(Scan.primary_emotion)
        .order_by(func.count(Scan.primary_emotion).desc())
        .limit(1)
    )
    top_row = top.first()
    return {
        "total_scans":       total or 0,
        "top_emotion":       top_row[0] if top_row else None,
        "top_emotion_count": top_row[1] if top_row else 0,
    }
