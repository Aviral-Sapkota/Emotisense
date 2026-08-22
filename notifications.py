# notifications.py


import json
import os
import logging

from pywebpush import webpush, WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import PushSubscription, NotificationRule
from schemas import EmotionResult

logger = logging.getLogger(__name__)

VAPID_PRIVATE = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_EMAIL   = os.environ.get("VAPID_EMAIL", "mailto:admin@emotisense.local")

EMOTION_EMOJI = {
    "angry":    "😠", "disgust": "🤢", "fear":    "😨",
    "happy":    "😄", "sad":     "😢", "surprise": "😮",
    "neutral":  "😐",
}


async def check_and_send_notifications(
    user_id: int,
    result:  EmotionResult,
    db:      AsyncSession,
) -> None:
    """Called as BackgroundTask after every /api/analyze request."""
    if not VAPID_PRIVATE:
        return  

    try:
        # Load user's enabled rules
        rows = await db.execute(
            select(NotificationRule).where(
                NotificationRule.user_id == user_id,
                NotificationRule.enabled == True,  
            )
        )
        rules = rows.scalars().all()
        if not rules:
            return

        # Find which rules are triggered
        triggered = [
            (rule, result.scores.get(rule.emotion, 0.0))
            for rule in rules
            if result.scores.get(rule.emotion, 0.0) >= rule.threshold
        ]
        if not triggered:
            return

        # Load all push subscriptions for this user
        subs_rows = await db.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
        subscriptions = subs_rows.scalars().all()
        if not subscriptions:
            return

        # Send a push for each triggered rule
        for rule, score in triggered:
            emoji = EMOTION_EMOJI.get(rule.emotion, "🎭")
            payload = json.dumps({
                "title": f"{emoji} Emotion Alert — {rule.emotion.capitalize()}",
                "body":  f"Detected at {score:.1f}% (your threshold: {rule.threshold:.0f}%)",
                "icon":  "/static/icons/icon-192.png",
                "data":  {"emotion": rule.emotion, "score": score, "url": "/demo"},
            })

            dead = []
            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {"p256dh": sub.p256dh, "auth": sub.auth_key},
                        },
                        data=payload,
                        vapid_private_key=VAPID_PRIVATE,
                        vapid_claims={"sub": VAPID_EMAIL},
                        ttl=60,
                    )
                except WebPushException as exc:
                    if getattr(exc.response, "status_code", None) == 410:
                        dead.append(sub)   # browser unsubscribed
                    else:
                        logger.warning("Push error sub=%s: %s", sub.id, exc)

            for d in dead:
                await db.delete(d)
            if dead:
                await db.commit()

    except Exception as exc:
        logger.error("Notification engine error: %s", exc, exc_info=True)
