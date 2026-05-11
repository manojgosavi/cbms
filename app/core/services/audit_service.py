"""
Audit service — write audit log entries consistently across the app.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.models.models import AuditLog
from app.core.services.auth_service import app_session


def log(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """
    Write a single audit log entry.
    Automatically picks up the current logged-in user.
    """
    user = app_session.current_user
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    session.add(entry)
