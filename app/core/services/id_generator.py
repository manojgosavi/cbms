"""
Sample ID generator.

Format: <PROJECT_SHORT>-<YY>-<SERIAL>
Example: COH-26-1, COH-26-2, DIAB-26-1

Serial is per (study × year), resets each calendar year.
Aliquot IDs extend samples: COH-26-1-A1, COH-26-1-A2 ...
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.models.models import Sample, SampleAliquot, Study


def generate_sample_id(session: Session, study: Study) -> str:
    """
    Generate the next Sample ID for a study in the current year.

    Steps:
    1. Find the highest serial already used for (study × year).
    2. Increment by 1.
    3. Return formatted ID.
    """
    year_short = str(dt.date.today().year)[-2:]       # "26"
    prefix = f"{study.project_id_short}-{year_short}-"

    # Find the current max serial for this prefix
    existing: list[Sample] = (
        session.query(Sample)
        .filter(Sample.sample_id.like(f"{prefix}%"))
        .all()
    )

    max_serial = 0
    for s in existing:
        try:
            serial = int(s.sample_id.replace(prefix, ""))
            max_serial = max(max_serial, serial)
        except ValueError:
            pass

    next_serial = max_serial + 1
    return f"{prefix}{next_serial}"


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
