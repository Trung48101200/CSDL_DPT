"""
Database module.
SQLAlchemy configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    # Use QueuePool for connection pooling with timeout
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using them
    echo=False,  # Set to True for SQL debug logging
)

# Create session factory bound to the engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency injection function to get database session.
    Used in FastAPI endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)


async def close_db():
    """Close database connections."""
    engine.dispose()
