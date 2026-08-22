# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Optional
from datetime import datetime


# Auth  

class UserRegister(BaseModel):
    first_name: str      = Field(..., min_length=1, max_length=50)
    last_name:  str      = Field(..., min_length=1, max_length=50)
    email:      EmailStr
    password:   str      = Field(..., min_length=6)

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    first_name:   str

class UserOut(BaseModel):
    id:         int
    email:      str
    first_name: str
    last_name:  str
    created_at: datetime
    model_config = {"from_attributes": True}


#  Analysis 

class AnalyzeRequest(BaseModel):
    # Base64-encoded JPEG from the browser webcam (no data-URL prefix)
    image: str

class EmotionResult(BaseModel):
    primary:        str                # e.g. "happy"
    confidence:     float              # top score 0–100
    scores:         Dict[str, float]   # all 7 emotions with percentages
    faces_detected: int                # 0 = no face found
    message:        Optional[str]      # e.g. "No face detected"

class ScanOut(BaseModel):
    id:              int
    primary_emotion: str
    confidence:      float
    scores:          Dict[str, float]
    faces_detected:  int
    created_at:      datetime
    model_config = {"from_attributes": True}


#  Push 

class PushSubscriptionIn(BaseModel):
    endpoint: str
    p256dh:   str
    auth:     str

class NotificationRuleIn(BaseModel):
    emotion:   str   = Field(..., example="angry")
    threshold: float = Field(..., ge=1, le=100, example=70)
    enabled:   bool  = True

class NotificationRuleOut(NotificationRuleIn):
    id: int
    model_config = {"from_attributes": True}
