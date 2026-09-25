from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    # SQLite is accessed from multiple threads (FastAPI + background ingestion)
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables if they don't exist. Call once at app startup."""
    from app.db import models  # noqa: F401 — ensure models are registered

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a short-lived session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
