"""
Shipment Service — ship blocked aliquots to a researcher.

Business rules:
  - Only blocked aliquots can be shipped (must be reserved first)
  - After shipment, the aliquot's location is preserved for grid history; the cell renders grey
  - Full shipment history is maintained
  - Shipment ref is auto-generated: SHIP-YYYYMMDD-NNN
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.models.models import (
    SampleAliquot, SampleBlock, Shipment, ShipmentItem
)
from app.core.services.audit_service import log
from app.core.services.auth_service import app_session
from app.config import AuditAction


def _generate_shipment_ref(session: Session) -> str:
    """Auto-generate a unique shipment reference: SHIP-20260318-001"""
    today = dt.date.today().strftime("%Y%m%d")
    prefix = f"SHIP-{today}-"
    count = (
        session.query(Shipment)
        .filter(Shipment.shipment_ref.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:03d}"


class ShipmentService:

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_shipment(
        self,
        aliquot_ids: List[int],
        recipient_name: str,
        recipient_institution: str = "",
        recipient_email: str = "",
        courier: str = "",
        tracking_number: str = "",
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Shipment]]:
        """
        Ship a list of aliquots.

        Steps per aliquot:
          1. Validate it is blocked (reserved)
          2. Mark as shipped, remove from location
          3. Release the block record
          4. Add to ShipmentItem list
        """
        app_session.require("shipment.create")

        if not recipient_name.strip():
            return False, "Recipient name is required.", None
        if not aliquot_ids:
            return False, "No aliquots selected.", None

        # Validate all aliquots before touching anything
        errors = []
        for aid in aliquot_ids:
            aliquot = self.session.get(SampleAliquot, aid)
            if not aliquot:
                errors.append(f"Aliquot ID {aid} not found.")
            elif aliquot.is_shipped:
                errors.append(f"{aliquot.aliquot_id} already shipped.")
            elif not aliquot.is_blocked:
                errors.append(f"{aliquot.aliquot_id} is not blocked — block it first.")

        if errors:
            return False, "\n".join(errors), None

        # Create shipment record
        ref = _generate_shipment_ref(self.session)
        user = app_session.current_user
        shipment = Shipment(
            shipment_ref=ref,
            recipient_name=recipient_name.strip(),
            recipient_institution=recipient_institution.strip(),
            recipient_email=recipient_email.strip(),
            shipped_by=user.username if user else "unknown",
            courier=courier.strip(),
            tracking_number=tracking_number.strip(),
            notes=notes.strip(),
        )
        self.session.add(shipment)
        self.session.flush()   # get shipment.id

        # Process each aliquot
        for aid in aliquot_ids:
            aliquot = self.session.get(SampleAliquot, aid)

            # Mark as shipped and no longer available
            aliquot.is_shipped   = True
            aliquot.is_blocked   = False
            aliquot.is_available = False
            self.session.add(aliquot)

            # Release the block record
            block = (
                self.session.query(SampleBlock)
                .filter(SampleBlock.aliquot_id == aid,
                        SampleBlock.is_released == False)
                .first()
            )
            if block:
                block.is_released = True
                block.released_at = dt.datetime.utcnow()
                self.session.add(block)

            # Add to shipment items
            self.session.add(ShipmentItem(
                shipment_id=shipment.id,
                aliquot_id=aid,
            ))

        self.session.flush()

        log(self.session, AuditAction.SHIP, "Shipment", ref,
            f"Shipment {ref}: {len(aliquot_ids)} aliquot(s) shipped to "
            f"'{recipient_name}' at '{recipient_institution}'.")

        return True, f"Shipment {ref} created with {len(aliquot_ids)} aliquot(s).", shipment

    # ── History ───────────────────────────────────────────────────────────

    def get_all_shipments(self) -> List[Shipment]:
        return (
            self.session.query(Shipment)
            .order_by(Shipment.shipped_at.desc())
            .all()
        )

    def get_shipment_items(self, shipment_id: int) -> List[ShipmentItem]:
        return (
            self.session.query(ShipmentItem)
            .filter(ShipmentItem.shipment_id == shipment_id)
            .all()
        )
