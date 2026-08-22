# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import create_access_token, get_current_user
from models import User
from schemas import TokenResponse, UserLogin, UserOut, UserRegister

router      = APIRouter(tags=["Authentication"])
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,
    deprecated="auto"
) 


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Create a new account. Returns a JWT token on success."""
    exists = await db.scalar(select(User).where(User.email == data.email.lower()))
    if exists:
        raise HTTPException(409, "An account with this email already exists.")

    user = User(
        email      = data.email.lower(),
        first_name = data.first_name.strip(),
        last_name  = data.last_name.strip(),
        hashed_pw  = pwd_context.hash(data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), first_name=user.first_name)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Sign in. Returns a JWT token on success."""
    user = await db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not pwd_context.verify(data.password, user.hashed_pw):
        raise HTTPException(401, "Incorrect email or password.")
    return TokenResponse(access_token=create_access_token(user.id), first_name=user.first_name)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Return the logged-in user's profile."""
    return current_user
