"""
Study Service — business logic for study/project management.

Key concept — what belongs in a service vs repository:
  Repository: "Give me all active studies"  (pure DB query)
  Service:    "Create a study, but first validate the short ID is uppercase,
               check it doesn't clash, then write an audit log entry"
              (decisions + orchestration)
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.models.models import Study, VisitDefinition
from app.core.repositories.study_repository import StudyRepository
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session
from app.config import AuditAction


class StudyService:

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = StudyRepository(session)

    # ── Create ─────────────────────────────────────────────────────────────

    def create_study(
        self,
        project_id_short: str,
        name: str,
        description: str = "",
        site_name: str = "",
        pi_name: str = "",
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
        visits: Optional[List[dict]] = None,
    ) -> tuple[bool, str, Optional[Study]]:
        """
        Create a new study.
        Returns (success, message, study_or_None).

        visits = [{"name": "Baseline", "code": "BL"}, ...]
        """
        app_session.require("study.create")

        # Normalise short ID to uppercase
        short_id = project_id_short.strip().upper()

        # Validate
        if not short_id:
            return False, "Project short ID is required.", None
        if len(short_id) > 10:
            return False, "Project short ID must be 10 characters or fewer.", None
        if not name.strip():
            return False, "Study name is required.", None
        if self.repo.short_id_exists(short_id):
            return False, f"Project ID '{short_id}' already exists.", None
        if self.repo.name_exists(name.strip()):
            return False, f"Study name '{name}' already exists.", None

        study = Study(
            project_id_short=short_id,
            name=name.strip(),
            description=description.strip(),
            site_name=site_name.strip(),
            pi_name=pi_name.strip(),
            start_date=start_date,
            end_date=end_date,
        )
        self.repo.add(study)

        # Add visit definitions if provided
        if visits:
            for i, v in enumerate(visits):
                self.repo.add_visit(VisitDefinition(
                    study_id=study.id,
                    visit_name=v.get("name", ""),
                    visit_code=v.get("code", ""),
                    order_index=i,
                ))

        log(self.session, AuditAction.CREATE, "Study", str(study.id),
            f"Study '{short_id}' created.")

        return True, "Study created successfully.", study

    # ── Read ───────────────────────────────────────────────────────────────

    def get_all_active(self) -> List[Study]:
        return self.repo.get_active()

    def get_by_id(self, study_id: int) -> Optional[Study]:
        return self.repo.get_by_id(study_id)

    # ── Update ─────────────────────────────────────────────────────────────

    def update_study(
        self,
        study_id: int,
        **fields,
    ) -> tuple[bool, str]:
        """Update mutable fields on an existing study."""
        app_session.require("study.edit")

        study = self.repo.get_by_id(study_id)
        if not study:
            return False, "Study not found."
        if study.is_locked:
            return False, "Study is locked. Unlock it before editing."

        allowed = {"name", "description", "site_name", "pi_name",
                   "start_date", "end_date", "is_active"}
        for key, value in fields.items():
            if key in allowed:
                setattr(study, key, value)

        self.repo.update(study)
        log(self.session, AuditAction.UPDATE, "Study", str(study_id),
            f"Study '{study.project_id_short}' updated.")
        return True, "Study updated."

    # ── Lock / Unlock ──────────────────────────────────────────────────────

    def set_lock(self, study_id: int, locked: bool) -> tuple[bool, str]:
        app_session.require("study.edit")
        study = self.repo.get_by_id(study_id)
        if not study:
            return False, "Study not found."
        study.is_locked = locked
        self.repo.update(study)
        action = "locked" if locked else "unlocked"
        log(self.session, AuditAction.UPDATE, "Study", str(study_id),
            f"Study '{study.project_id_short}' {action}.")
        return True, f"Study {action}."

    # ── Delete ─────────────────────────────────────────────────────────────

    def delete_study(self, study_id: int, reason: str) -> tuple[bool, str]:
        app_session.require("study.delete")

        study = self.repo.get_by_id(study_id)
        if not study:
            return False, "Study not found."
        if not reason.strip():
            return False, "A reason is required for deletion."
        if study.participants:
            return False, (
                f"Cannot delete: study has {len(study.participants)} participant(s). "
                "Archive it instead."
            )

        name = study.project_id_short
        self.repo.delete(study)
        log(self.session, AuditAction.DELETE, "Study", str(study_id),
            f"Study '{name}' deleted. Reason: {reason}")
        return True, "Study deleted."
