# Plan — Storage Data Migration

**Branch:** `feature/storage-data-migration`  
**Estimated effort:** 30 minutes  
**Files created:** 1 (`migrate_storage.py` at project root)

---

## Task Group 1 — Write migrate_storage.py

Create the script at the project root. It must:
- Resolve the DB path via `app.config.DB_PATH`
- Print a pre-migration summary
- Ask for confirmation (unless `--yes` is passed)
- Delete all storage rows in dependency order
- Print a post-migration summary
- Exit with code 0 on success, 1 on error

```python
#!/usr/bin/env python3
"""
Storage hierarchy migration script.

Clears all storage-related data (Freezer/Compartment/Rack/Drawer/Box/
BoxPosition/AliquotLocation) while keeping Participant, Sample, and
SampleAliquot records intact.

After running this script:
  1. Open the CBMS app
  2. Go to Participants tab → Import from Excel
  3. Select CBMS_Dummy_Data.xlsx
  The fixed import service will create the correct storage hierarchy.

Usage:
  python migrate_storage.py          # interactive (asks for confirmation)
  python migrate_storage.py --yes    # skip confirmation prompt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import DB_PATH
from app.core.models.database import engine
from app.core.models.models import (
    AliquotLocation, BoxPosition, StorageBox, StorageDrawer,
    StorageRack, Compartment, Freezer, SampleAliquot,
)
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)


def _count(session, model) -> int:
    return session.query(model).count()


def migrate(skip_confirm: bool = False) -> None:
    session = Session()
    try:
        # ── Pre-migration summary ──────────────────────────────────────────
        n_freezers    = _count(session, Freezer)
        n_comps       = _count(session, Compartment)
        n_racks       = _count(session, StorageRack)
        n_drawers     = _count(session, StorageDrawer)
        n_boxes       = _count(session, StorageBox)
        n_positions   = _count(session, BoxPosition)
        n_locations   = _count(session, AliquotLocation)
        n_aliquots    = _count(session, SampleAliquot)

        print("\n── Storage Data Migration ────────────────────────────────")
        print(f"  DB path          : {DB_PATH}")
        print(f"  Freezers         : {n_freezers}")
        print(f"  Compartments     : {n_comps}")
        print(f"  Racks            : {n_racks}")
        print(f"  Drawers          : {n_drawers}")
        print(f"  Boxes            : {n_boxes}")
        print(f"  Box Positions    : {n_positions}")
        print(f"  Aliquot Locations: {n_locations}")
        print(f"  Aliquots (kept)  : {n_aliquots}")
        print("──────────────────────────────────────────────────────────")

        if n_freezers == 0 and n_locations == 0:
            print("✅  Nothing to migrate — storage tables are already empty.")
            return

        if not skip_confirm:
            ans = input("\nThis will DELETE all storage hierarchy and aliquot "
                        "location data.\nParticipant/Sample/Aliquot records are "
                        "kept.\nProceed? [y/N]: ").strip().lower()
            if ans != "y":
                print("Aborted.")
                return

        # ── Delete in dependency order ─────────────────────────────────────
        print("\nDeleting storage data…")
        session.query(AliquotLocation).delete()
        session.query(BoxPosition).delete()
        # Delete child boxes first (parent_box_id FK)
        session.query(StorageBox).filter(StorageBox.parent_box_id.isnot(None)).delete()
        session.query(StorageBox).delete()
        session.query(StorageDrawer).delete()
        session.query(StorageRack).delete()
        session.query(Compartment).delete()
        session.query(Freezer).delete()
        session.commit()

        # ── Post-migration check ───────────────────────────────────────────
        remaining_aliquots = _count(session, SampleAliquot)

        print("✅  Migration complete.")
        print(f"   Aliquots preserved: {remaining_aliquots} (was {n_aliquots})")
        print("\nNext steps:")
        print("  1. Open the CBMS app")
        print("  2. Participants tab → Import from Excel")
        print("  3. Select your Excel file (e.g. CBMS_Dummy_Data.xlsx)")
        print("  4. The correct storage hierarchy will be created on import.")

    except Exception as e:
        session.rollback()
        print(f"\n❌  Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    skip = "--yes" in sys.argv
    migrate(skip_confirm=skip)
```

---

## Task Group 2 — Update docs

2.1 Strike the TODO item in `specs/TODO.md`.

2.2 Add entry to `specs/constitution.md` §15 changelog.

---

## Task Group 3 — Commit

```
fix(migration): add migrate_storage.py to clear wrong storage hierarchy

Clears AliquotLocation, BoxPosition, StorageBox, StorageDrawer,
StorageRack, Compartment, and Freezer rows while preserving all
Participant/Sample/SampleAliquot records. After running, user
reimports Excel to get the correct hierarchy via the fixed service.
```
