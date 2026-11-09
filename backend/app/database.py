"""
Database engine and session management.
Uses SQLAlchemy 2.x async engine with asyncpg driver.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def create_engine(settings: Settings):  # type: ignore[no-untyped-def]
    is_sqlite = "sqlite" in settings.database_url
    kwargs: dict = {
        "pool_pre_ping": True,
        "echo": not settings.is_production,
    }
    if not is_sqlite:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return create_async_engine(settings.database_url, **kwargs)


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(settings)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# Module-level session factory — initialized on first use
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        settings = get_settings()
        _session_factory = create_session_factory(settings)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for use in route handlers
DbSession = Annotated[AsyncSession, Depends(get_db)]
