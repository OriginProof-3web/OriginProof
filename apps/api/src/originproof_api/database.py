from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from originproof_core import DependencyUnavailableError
from sqlalchemy import JSON, DateTime, String, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SignedProofRow(Base):
    __tablename__ = "signed_proofs"

    proof_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def sessions(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def ping(self) -> None:
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as error:
            raise DependencyUnavailableError("database is unavailable") from error

    async def dispose(self) -> None:
        await self.engine.dispose()
