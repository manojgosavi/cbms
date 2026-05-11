"""
Authentication service.
Handles password hashing, login verification, and the current session user.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from app.core.models.models import AuditLog, User
from app.config import AuditAction, Role


# ── Password helpers ───────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Session state (simple in-process singleton) ───────────────────────────

class _AppSession:
    """
    Holds the currently logged-in user for the lifetime of the process.

    Key lesson — why we store primitives, not the ORM object:
      SQLAlchemy objects are tied to the Session that loaded them.
      When the session closes (end of `with get_session()`), the object
      becomes "detached". Accessing any attribute on it triggers a
      lazy-load, which needs an open session — and crashes.

      Solution: copy the values we need into plain Python strings/ints
      immediately after login, while the session is still open.
      Strings are never detached — they're just strings.
    """

    def __init__(self):
        self._user_id:   Optional[int] = None
        self._username:  Optional[str] = None
        self._role:      Optional[str] = None
        self._email:     Optional[str] = None

    # ── Read-only properties ───────────────────────────────────────────────

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def email(self) -> Optional[str]:
        return self._email

    @property
    def is_authenticated(self) -> bool:
        return self._user_id is not None

    # Keep current_user as a property that returns a simple namespace
    # so existing code like app_session.current_user.username still works
    @property
    def current_user(self):
        if not self.is_authenticated:
            return None
        # Return a simple object with the stored primitive values
        class _UserProxy:
            pass
        proxy = _UserProxy()
        proxy.id       = self._user_id
        proxy.username = self._username
        proxy.role     = self._role
        proxy.email    = self._email
        return proxy

    def login(self, user: User) -> None:
        # Copy primitives NOW while the session is open
        self._user_id  = user.id
        self._username = user.username
        self._role     = user.role
        self._email    = user.email

    def logout(self) -> None:
        self._user_id  = None
        self._username = None
        self._role     = None
        self._email    = None

    def can(self, action: str) -> bool:
        if self._role is None:
            return False
        return Role.can(self._role, action)

    def require(self, action: str) -> None:
        if not self.can(action):
            raise PermissionError(
                f"Action '{action}' not permitted for role "
                f"'{self._role if self._role else 'anonymous'}'"
            )


app_session = _AppSession()


# ── Service functions ──────────────────────────────────────────────────────

def login(session: Session, username: str, password: str) -> tuple[bool, str]:
    """
    Attempt login. Returns (success, message).
    On success, sets app_session.current_user.
    """
    user: Optional[User] = session.query(User).filter_by(username=username).first()

    if user is None:
        return False, "User not found."
    if not user.is_approved:
        return False, "Account pending approval."
    if not user.is_active:
        return False, "Account is disabled."
    if not verify_password(password, user.password_hash):
        return False, "Incorrect password."

    user.last_login = dt.datetime.utcnow()
    session.add(AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        entity_type="User",
        entity_id=str(user.id),
        description=f"User '{user.username}' logged in.",
    ))
    app_session.login(user)
    return True, "Login successful."


def logout(session: Session) -> None:
    user = app_session.current_user
    if user:
        session.add(AuditLog(
            user_id=user.id,
            action=AuditAction.LOGOUT,
            entity_type="User",
            entity_id=str(user.id),
            description=f"User '{user.username}' logged out.",
        ))
    app_session.logout()


def register_user(
    session: Session,
    username: str,
    email: str,
    password: str,
    role: str,
    auto_approve: bool = False,
) -> tuple[bool, str]:
    """Create a new user. Returns (success, message)."""
    if session.query(User).filter_by(username=username).first():
        return False, f"Username '{username}' already exists."
    if session.query(User).filter_by(email=email).first():
        return False, f"Email '{email}' already registered."
    if role not in Role.ALL:
        return False, f"Invalid role '{role}'."

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_approved=auto_approve,
    )
    session.add(user)
    session.flush()  # get the id

    session.add(AuditLog(
        user_id=app_session.current_user.id if app_session.current_user else None,
        action=AuditAction.CREATE,
        entity_type="User",
        entity_id=str(user.id),
        description=f"User '{username}' registered with role '{role}'.",
    ))
    return True, "User created successfully."


def seed_admin(session: Session) -> None:
    """Create a default admin/PI account if no users exist."""
    if session.query(User).count() == 0:
        session.add(User(
            username="admin",
            email="admin@cbms.local",
            password_hash=hash_password("Admin@1234"),
            role=Role.PI,
            is_active=True,
            is_approved=True,
        ))
        print("[CBMS] Default admin created — username: admin / password: Admin@1234")
        print("[CBMS] Please change the password after first login.")
