"""
Admin Service — user management, permissions, custom fields, audit retrieval.

Key concept — why admin logic is a separate service:
  Auth service handles login/logout (identity).
  Admin service handles governance (who can do what, viewing history).
  Keeping them separate means a lab tech can log in without having
  access to any admin_service methods — the RBAC check at the top
  of each method enforces this.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.models.models import (
    AuditLog, CustomFieldDefinition, User
)
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session, hash_password
from app.config import AuditAction, Role


class AdminService:

    def __init__(self, session: Session) -> None:
        self.session = session

    # ══════════════════════════════════════════════════════════════════════
    # USER MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════

    def get_all_users(self) -> List[User]:
        app_session.require("admin.users")
        return (
            self.session.query(User)
            .order_by(User.username)
            .all()
        )

    def approve_user(self, user_id: int) -> Tuple[bool, str]:
        app_session.require("admin.users")
        user = self.session.get(User, user_id)
        if not user:
            return False, "User not found."
        if user.is_approved:
            return False, "User is already approved."
        user.is_approved = True
        self.session.add(user)
        self.session.flush()
        log(self.session, AuditAction.UPDATE, "User", str(user_id),
            f"User '{user.username}' approved.")
        return True, f"User '{user.username}' approved."

    def update_user(
        self,
        user_id: int,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        email: Optional[str] = None,
    ) -> Tuple[bool, str]:
        app_session.require("admin.users")
        user = self.session.get(User, user_id)
        if not user:
            return False, "User not found."

        # Prevent demoting yourself
        current = app_session.current_user
        if current and current.id == user_id and role and role != user.role:
            return False, "You cannot change your own role."

        if role:
            if role not in Role.ALL:
                return False, f"Invalid role '{role}'."
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if email:
            user.email = email.strip()

        self.session.add(user)
        self.session.flush()
        log(self.session, AuditAction.UPDATE, "User", str(user_id),
            f"User '{user.username}' updated.")
        return True, "User updated."

    def reset_password(
        self, user_id: int, new_password: str
    ) -> Tuple[bool, str]:
        app_session.require("admin.users")
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters."
        user = self.session.get(User, user_id)
        if not user:
            return False, "User not found."
        user.password_hash = hash_password(new_password)
        self.session.add(user)
        self.session.flush()
        log(self.session, AuditAction.UPDATE, "User", str(user_id),
            f"Password reset for '{user.username}'.")
        return True, "Password reset successfully."

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        app_session.require("admin.users")
        current = app_session.current_user
        if current and current.id == user_id:
            return False, "You cannot delete your own account."
        user = self.session.get(User, user_id)
        if not user:
            return False, "User not found."
        username = user.username
        self.session.delete(user)
        self.session.flush()
        log(self.session, AuditAction.DELETE, "User", str(user_id),
            f"User '{username}' deleted.")
        return True, f"User '{username}' deleted."

    # ══════════════════════════════════════════════════════════════════════
    # AUDIT TRAIL
    # ══════════════════════════════════════════════════════════════════════

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        date_from: Optional[dt.date] = None,
        date_to: Optional[dt.date] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[AuditLog], int]:
        """
        Filterable audit log query.
        Returns (logs, total_count).
        """
        app_session.require("admin.audit")
        q = self.session.query(AuditLog)

        if user_id:
            q = q.filter(AuditLog.user_id == user_id)
        if action:
            q = q.filter(AuditLog.action == action)
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        if date_from:
            q = q.filter(AuditLog.timestamp >= dt.datetime.combine(date_from, dt.time.min))
        if date_to:
            q = q.filter(AuditLog.timestamp <= dt.datetime.combine(date_to, dt.time.max))

        total = q.count()
        logs = (
            q.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return logs, total

    # ══════════════════════════════════════════════════════════════════════
    # CUSTOM FIELD DEFINITIONS
    # ══════════════════════════════════════════════════════════════════════

    def get_custom_fields(self) -> List[CustomFieldDefinition]:
        return (
            self.session.query(CustomFieldDefinition)
            .order_by(CustomFieldDefinition.field_label)
            .all()
        )

    def add_custom_field(
        self,
        field_name: str,
        field_label: str,
        field_type: str = "text",
    ) -> Tuple[bool, str]:
        app_session.require("admin.users")
        field_name = field_name.strip().lower().replace(" ", "_")
        if not field_name or not field_label.strip():
            return False, "Field name and label are required."

        existing = (
            self.session.query(CustomFieldDefinition)
            .filter(CustomFieldDefinition.field_name == field_name)
            .first()
        )
        if existing:
            return False, f"Custom field '{field_name}' already exists."

        cf = CustomFieldDefinition(
            field_name=field_name,
            field_label=field_label.strip(),
            field_type=field_type,
        )
        self.session.add(cf)
        self.session.flush()
        log(self.session, AuditAction.CREATE, "CustomField", str(cf.id),
            f"Custom field '{field_name}' created.")
        return True, "Custom field added."

    def toggle_custom_field(self, field_id: int) -> Tuple[bool, str]:
        app_session.require("admin.users")
        cf = self.session.get(CustomFieldDefinition, field_id)
        if not cf:
            return False, "Field not found."
        cf.is_active = not cf.is_active
        self.session.add(cf)
        self.session.flush()
        state = "enabled" if cf.is_active else "disabled"
        return True, f"Field '{cf.field_label}' {state}."
