"""
Base Repository — generic CRUD that all repositories inherit from.

Pattern explanation:
  Every repository gets Create, Read, Update, Delete for free.
  Specific repositories (StudyRepository, ParticipantRepository, etc.)
  inherit this and add their own query methods on top.

  T = the SQLAlchemy model type (e.g. Study, Participant)
"""

from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.models.models import Base

# TypeVar lets Python know T is always a SQLAlchemy model subclass
T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic repository providing basic CRUD operations.

    Usage:
        class StudyRepository(BaseRepository[Study]):
            def __init__(self, session):
                super().__init__(session, Study)
    """

    def __init__(self, session: Session, model: Type[T]) -> None:
        self.session = session
        self.model = model

    # ── Create ─────────────────────────────────────────────────────────────

    def add(self, entity: T) -> T:
        """Persist a new entity. Returns the entity with its id populated."""
        self.session.add(entity)
        self.session.flush()   # flush → assigns PK without committing
        return entity

    # ── Read ───────────────────────────────────────────────────────────────

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Fetch a single record by primary key. Returns None if not found."""
        return self.session.get(self.model, entity_id)

    def get_all(self) -> List[T]:
        """Return every row for this model."""
        return self.session.query(self.model).all()

    def count(self) -> int:
        """Total row count."""
        return self.session.query(self.model).count()

    # ── Update ─────────────────────────────────────────────────────────────

    def update(self, entity: T) -> T:
        """
        Mark entity as modified and flush.
        Caller is responsible for mutating the entity fields before calling this.
        """
        self.session.add(entity)
        self.session.flush()
        return entity

    # ── Delete ─────────────────────────────────────────────────────────────

    def delete(self, entity: T) -> None:
        """Remove entity from DB."""
        self.session.delete(entity)
        self.session.flush()
