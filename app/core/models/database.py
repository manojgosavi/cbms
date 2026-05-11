"""
Database engine, session factory, and initialisation helpers.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL, DATA_DIR
from app.core.models.models import Base


# ── Engine ─────────────────────────────────────────────────────────────────

def _get_engine(url: str = DATABASE_URL) -> Engine:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},  # required for SQLite
        echo=False,
    )
    # Enable WAL mode for better concurrent read performance on SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── Helpers ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables — use only in tests."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context-manager that yields a session and handles commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
