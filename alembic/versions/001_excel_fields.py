"""
Migration 001: add fields derived from Sample_Datasheet Excel analysis.

New fields:
  participants       → disease
  storage_boxes      → shelf, rack
  sample_aliquots    → legacy_id, discrepancy_remark, discrepancy_field

This migration uses column existence checks before adding, so it is safe
to run even if some columns were added manually or via init_db().
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists — prevents 'duplicate column' errors."""
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def _add_if_missing(table: str, column: str, col_type):
    if not _column_exists(table, column):
        op.add_column(table, sa.Column(column, col_type, nullable=True))
        print(f"  Added {table}.{column}")
    else:
        print(f"  Skipped {table}.{column} (already exists)")


def upgrade():
    _add_if_missing('participants',    'disease',             sa.String(64))
    _add_if_missing('storage_boxes',   'shelf',               sa.String(32))
    _add_if_missing('storage_boxes',   'rack',                sa.String(32))
    _add_if_missing('sample_aliquots', 'legacy_id',           sa.String(64))
    _add_if_missing('sample_aliquots', 'discrepancy_remark',  sa.Text)
    _add_if_missing('sample_aliquots', 'discrepancy_field',   sa.String(64))


def downgrade():
    # SQLite does not support DROP COLUMN — no-op
    pass
