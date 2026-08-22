# models.py


from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name  = Column(String, nullable=False)
    hashed_pw  = Column(String, nullable=False)   
    created_at = Column(DateTime, default=datetime.utcnow)

    
    scans       = relationship("Scan",             back_populates="user", cascade="all, delete")
    push_subs   = relationship("PushSubscription", back_populates="user", cascade="all, delete")
    notif_rules = relationship("NotificationRule", back_populates="user", cascade="all, delete")


class Scan(Base):
    """One row = one webcam analysis result."""
    __tablename__ = "scans"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    primary_emotion = Column(String,  nullable=False)   # e.g. "happy"
    confidence      = Column(Float,   nullable=False)   # top score as %
    scores          = Column(JSON,    nullable=False)   # {"happy":87.3, "sad":2.1, ...}
    faces_detected  = Column(Integer, default=1)        # how many faces were found
    created_at      = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="scans")


class PushSubscription(Base):
    """Browser push subscription — one row per device that enabled notifications."""
    __tablename__ = "push_subscriptions"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)   # unique URL per device
    p256dh   = Column(String, nullable=False)   # browser encryption key
    auth_key = Column(String, nullable=False)   # auth secret

    user = relationship("User", back_populates="push_subs")


class NotificationRule(Base):
    """A rule: 'notify me when <emotion> score >= <threshold>%'."""
    __tablename__ = "notification_rules"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    emotion   = Column(String,  nullable=False)   
    threshold = Column(Float,   nullable=False)   
    enabled   = Column(Boolean, default=True)

    user = relationship("User", back_populates="notif_rules")
