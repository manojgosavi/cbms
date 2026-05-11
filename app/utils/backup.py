"""
Backup utility — copies cbms.db to the backups folder with a timestamp.

Key concept — shutil.copy2:
  copy2 preserves file metadata (timestamps).
  We use it instead of reading/writing bytes manually.
  The backup filename includes a timestamp so each backup is unique.
"""

import shutil
import datetime as dt
from pathlib import Path
from typing import Tuple

from app.config import DB_PATH, BACKUP_DIR


def run_backup() -> Tuple[bool, str]:
    """
    Copy the live database to the backups folder.
    Returns (success, path_or_error_message).
    """
    if not DB_PATH.exists():
        return False, "Database file does not exist yet."

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"cbms_{timestamp}.db"

    try:
        shutil.copy2(DB_PATH, dest)
        return True, str(dest)
    except Exception as e:
        return False, str(e)
