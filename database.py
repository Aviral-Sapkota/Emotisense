# database.py
# Handles the connection to PostgreSQL using SQLAlchemy (async version).

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")


engine = create_async_engine(
    DATABASE_URL,
    echo=False,       # set True to print every SQL query (helpful for debugging)
    pool_size=10,     
    max_overflow=20,  # allow up to 20 extra connections under heavy load
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables on startup if they don't exist yet."""
    from models import User, Scan, PushSubscription, NotificationRule  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields one DB session per request, auto-closes it."""
    async with SessionLocal() as session:
        yield session
