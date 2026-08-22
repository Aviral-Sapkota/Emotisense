# routers/push.py
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models import NotificationRule, PushSubscription, User
from schemas import NotificationRuleIn, NotificationRuleOut, PushSubscriptionIn

router = APIRouter(prefix="/push", tags=["Push Notifications"])

VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC_KEY", "")
VALID_EMOTIONS = {"angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"}


@router.get("/vapid-public-key")
async def vapid_public_key():
    if not VAPID_PUBLIC:
        raise HTTPException(503, "Push notifications are not configured on this server.")
    return {"public_key": VAPID_PUBLIC}


@router.post("/subscribe", status_code=201)
async def subscribe(
    body: PushSubscriptionIn,
    
    db:   AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id  == 1,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    if existing:
        return {"status": "already subscribed"}
    db.add(PushSubscription(
        user_id  = 1,
        endpoint = body.endpoint,
        p256dh   = body.p256dh,
        auth_key = body.auth,
    ))
    await db.commit()
    return {"status": "subscribed"}


@router.delete("/unsubscribe")
async def unsubscribe(
    endpoint: str,
    
    db:   AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id  == 1,
            PushSubscription.endpoint == endpoint,
        )
    )
    await db.commit()
    return {"status": "unsubscribed"}


@router.get("/rules", response_model=list[NotificationRuleOut])
async def list_rules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(NotificationRule).where(NotificationRule.user_id == user.id))
    return rows.scalars().all()


@router.post("/rules", response_model=NotificationRuleOut, status_code=201)
async def create_rule(
    body: NotificationRuleIn,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    if body.emotion not in VALID_EMOTIONS:
        raise HTTPException(400, f"Invalid emotion. Choose from: {', '.join(sorted(VALID_EMOTIONS))}")
    existing = await db.scalar(
        select(NotificationRule).where(
            NotificationRule.user_id == user.id,
            NotificationRule.emotion == body.emotion,
        )
    )
    if existing:
        raise HTTPException(409, f"A rule for '{body.emotion}' already exists. Delete it first.")
    rule = NotificationRule(user_id=user.id, emotion=body.emotion, threshold=body.threshold, enabled=body.enabled)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=NotificationRuleOut)
async def update_rule(
    rule_id: int,
    body:    NotificationRuleIn,
    user:    User         = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    rule = await db.get(NotificationRule, rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(404, "Rule not found.")
    rule.threshold = body.threshold
    rule.enabled   = body.enabled
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    user:    User         = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    rule = await db.get(NotificationRule, rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(404, "Rule not found.")
    await db.delete(rule)
    await db.commit()
