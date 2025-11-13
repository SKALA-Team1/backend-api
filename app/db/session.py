"""SQLAlchemy engine and scoped session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    """Return a plain SQLAlchemy session (useful outside FastAPI dependencies)."""
    return SessionLocal()
