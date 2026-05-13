"""
Blocking Service — lock aliquots for a researcher for a defined time window.

Business rules (from scope document):
  - Blocked aliquots cannot be edited, moved, or shipped to anyone else
  - If not shipped within the timeframe, the system prompts user to release
  - User can extend the time window with a reason
  - After release, aliquot returns to available pool
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.models.models import SampleAliquot, SampleBlock
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session
from app.config import AuditAction


class BlockingService:

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Block ──────────────────────────────────────────────────────────────

    def block_aliquots(
        self,
        aliquot_ids: List[int],
        blocked_by: str,
        unblock_date: dt.date,
        reason: str = "",
    ) -> Tuple[bool, str, dict]:
        """
        Block a list of aliquots for a researcher until unblock_date.
        Returns (success, message, {blocked: N, skipped: [(id, reason)]})
        """
        app_session.require("sample.edit")

        if not blocked_by.strip():
            return False, "Researcher name is required.", {}
        if unblock_date <= dt.date.today():
            return False, "Unblock date must be in the future.", {}
        if not reason.strip():
            return False, "A reason is required for blocking.", {}

        blocked_count = 0
        skipped = []

        for aliquot_id in aliquot_ids:
            aliquot = self.session.get(SampleAliquot, aliquot_id)
            if not aliquot:
                skipped.append((aliquot_id, "Not found"))
                continue
            if aliquot.is_blocked:
                skipped.append((aliquot_id, "Already blocked"))
                continue
            if aliquot.is_shipped:
                skipped.append((aliquot_id, "Already shipped"))
                continue
            if not aliquot.is_available:
                skipped.append((aliquot_id, "Not available"))
                continue

            # Set block flag on aliquot
            aliquot.is_blocked = True
            self.session.add(aliquot)

            # Create SampleBlock record
            block = SampleBlock(
                aliquot_id=aliquot_id,
                blocked_by=blocked_by.strip(),
                unblock_at=dt.datetime.combine(unblock_date, dt.time.min),
                reason=reason.strip(),
            )
            self.session.add(block)
            blocked_count += 1

        if blocked_count == 0:
            return False, "No aliquots were blocked.", {"blocked": 0, "skipped": skipped}

        self.session.flush()
        log(self.session, AuditAction.BLOCK, "SampleAliquot", None,
            f"{blocked_count} aliquot(s) blocked for '{blocked_by}' until {unblock_date}. "
            f"Reason: {reason}")

        msg = f"{blocked_count} aliquot(s) blocked."
        if skipped:
            msg += f" {len(skipped)} skipped."
        return True, msg, {"blocked": blocked_count, "skipped": skipped}

    # ── Release ────────────────────────────────────────────────────────────

    def release_block(
        self,
        aliquot_id: int,
        reason: str = "Released by user",
    ) -> Tuple[bool, str]:

        aliquot = self.session.get(SampleAliquot, aliquot_id)
        if not aliquot:
            return False, "Aliquot not found."
        if not aliquot.is_blocked:
            return False, "Aliquot is not blocked."

        block = (
            self.session.query(SampleBlock)
            .filter(SampleBlock.aliquot_id == aliquot_id,
                    SampleBlock.is_released == False)
            .first()
        )
        if block:
            block.is_released = True
            block.released_at = dt.datetime.utcnow()
            self.session.add(block)

        aliquot.is_blocked = False
        self.session.add(aliquot)
        self.session.flush()

        log(self.session, AuditAction.UNBLOCK, "SampleAliquot", str(aliquot_id),
            f"Aliquot {aliquot.aliquot_id} released. Reason: {reason}")
        return True, "Block released."

    def release_multiple(
        self,
        aliquot_ids: List[int],
        reason: str,
    ) -> Tuple[bool, str]:
        released = 0
        for aid in aliquot_ids:
            ok, _ = self.release_block(aid, reason)
            if ok:
                released += 1
        return True, f"{released} aliquot(s) released."

    # ── Extend ────────────────────────────────────────────────────────────

    def extend_block(
        self,
        aliquot_id: int,
        new_unblock_date: dt.date,
        reason: str,
    ) -> Tuple[bool, str]:
        app_session.require("sample.edit")

        if not reason.strip():
            return False, "A reason is required to extend a block."
        if new_unblock_date <= dt.date.today():
            return False, "New unblock date must be in the future."

        block = (
            self.session.query(SampleBlock)
            .filter(SampleBlock.aliquot_id == aliquot_id,
                    SampleBlock.is_released == False)
            .first()
        )
        if not block:
            return False, "No active block found for this aliquot."

        old_date = block.unblock_at
        block.unblock_at = dt.datetime.combine(new_unblock_date, dt.time.min)
        self.session.add(block)
        self.session.flush()

        log(self.session, AuditAction.UPDATE, "SampleBlock", str(block.id),
            f"Block extended from {old_date.date()} to {new_unblock_date}. Reason: {reason}")
        return True, f"Block extended to {new_unblock_date}."

    # ── Overdue check ─────────────────────────────────────────────────────

    def get_overdue_blocks(self) -> List[SampleBlock]:
        """
        Return blocks whose unblock_at has passed but are not yet released.
        The UI calls this on startup to prompt the user.
        """
        now = dt.datetime.utcnow()
        return (
            self.session.query(SampleBlock)
            .filter(
                SampleBlock.is_released == False,
                SampleBlock.unblock_at <= now,
            )
            .all()
        )
