"""
Sample ID generator.

Format: <PROJECT_SHORT>-<YY>-<SERIAL>
Example: COH-26-1, COH-26-2, DIAB-26-1

Serial is per (study × year), resets each calendar year.
Aliquot IDs extend samples: COH-26-1-A1, COH-26-1-A2 ...
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.models.models import Sample, SampleAliquot, Study


def generate_sample_id(session: Session, study: Study) -> str:
    """
    Generate the next Sample ID for a study in the current year.

    Uses func.max() to find the highest serial in one query (O(1)).
    """
    year_short = str(dt.date.today().year)[-2:]
    prefix = f"{study.project_id_short}-{year_short}-"

    max_id = (
        session.query(func.max(Sample.sample_id))
        .filter(Sample.sample_id.like(f"{prefix}%"))
        .scalar()
    )

    max_serial = 0
    if max_id:
        try:
            max_serial = int(max_id.replace(prefix, ""))
        except ValueError:
            pass

    return f"{prefix}{max_serial + 1}"


def generate_aliquot_id(sample_id: str, aliquot_number: int) -> str:
    """
    Derive an aliquot ID from a sample ID.
    Example: COH-26-1 + 1  →  COH-26-1-A1
    """
    return f"{sample_id}-A{aliquot_number}"


def next_aliquot_number(session: Session, sample_id_pk: int) -> int:
    """Return the next aliquot number for a given sample (1-indexed)."""
    count = (
        session.query(SampleAliquot)
        .filter(SampleAliquot.sample_id == sample_id_pk)
        .count()
    )
    return count + 1
