"""
Shared pytest fixtures for integration tests: builds the schema against
DATABASE_URL (expected to point at a disposable test Postgres — see
docker-compose.yml `db` service or CI's postgres service container), yields
an AsyncSession per test wrapped in a transaction that's rolled back
afterward so tests don't leak state into each other.
"""
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
# Import every model so Base.metadata is fully populated before create_all.
from app.models import (  # noqa: F401
    audit_log,
    maintenance_window,
    operating_system,
    user,
    vm_limit_policy,
    vm_session,
)

settings = get_settings()


@pytest_asyncio.fixture(scope="session")
async def _engine():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncSession:
    connection = await _engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
