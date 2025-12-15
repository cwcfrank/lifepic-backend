"""
Database connection and session management.
Uses SQLAlchemy async with asyncpg for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_async_database_url(url: str) -> str:
    """
    Convert postgres:// to postgresql+asyncpg:// for async driver.
    Also convert sslmode=require to ssl=require for asyncpg compatibility.
    """
    # Convert protocol
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Convert sslmode to ssl for asyncpg
    url = url.replace("sslmode=", "ssl=")
    
    return url


settings = get_settings()

# Create async engine
engine = create_async_engine(
    get_async_database_url(settings.database_url),
    echo=settings.debug,
    pool_pre_ping=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
