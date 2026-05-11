# Validation — Storage Data Migration

**Method:** Manual check  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** All checks must pass before merging to `main`

---

## Pre-conditions

- [ ] `data/cbms.db` has been populated with previously imported data (wrong hierarchy exists).
- [ ] Terminal is open in the project root.
- [ ] Virtual environment is activated: `source venv/bin/activate`

---

## Step 1 — Run the migration script

```bash
python migrate_storage.py
```

### SC-1 — Pre-migration summary prints correctly

- [ ] Script prints counts of Freezers, Compartments, Racks, Drawers, Boxes, Positions, Aliquot Locations before deleting.
- [ ] Aliquot count (`Aliquots (kept)`) shows the number of SampleAliquot records (should be 27).
- [ ] Confirmation prompt appears.

### SC-2 — Confirm and migrate

- [ ] Type `y` at the prompt.
- [ ] Script prints `✅  Migration complete.`
- [ ] `Aliquots preserved: 27 (was 27)` — count unchanged.
- [ ] Next steps are printed.
- [ ] No Python traceback.

### SC-3 — Second run is safe (idempotent)

- [ ] Run `python migrate_storage.py --yes` again.
- [ ] Script prints `✅  Nothing to migrate — storage tables are already empty.`
- [ ] No error.

---

## Step 2 — Verify storage tables are empty

```bash
python3 -c "
from app.core.models.database import get_session
from app.core.models.models import Freezer, AliquotLocation, SampleAliquot
with get_session() as s:
    print('Freezers:', s.query(Freezer).count())
    print('AliquotLocations:', s.query(AliquotLocation).count())
    print('SampleAliquots:', s.query(SampleAliquot).count())
"
```

- [ ] `Freezers: 0`
- [ ] `AliquotLocations: 0`
- [ ] `SampleAliquots: 27` (unchanged)

---

## Step 3 — Reimport from Excel

- [ ] Open the CBMS app (`python main.py`).
- [ ] Navigate to **Participants tab** → click **Import from Excel**.
- [ ] Select `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`.
- [ ] Import completes without errors.

---

## Step 4 — Verify correct hierarchy in Storage tab

- [ ] Open **Storage tab**.
- [ ] Expand freezer `NARI/COHRPICA/18-19/01 REGULAR`.
- [ ] Level-2 nodes (Shelf) show Roman numerals: `I`, `II`, `III` — **not** box names like `COHNSSER3-R HIV UNINFECTED`.
- [ ] Drill down: Shelf `III` → Rack `D` → Drawer `02` → Box `COHNSSER3-R HIV UNINFECTED`.
- [ ] The Box node shows the correct container name.
- [ ] No node named `Box-1` anywhere in the tree.

### SC-4 — Box grid shows aliquot positions

- [ ] Click a Box node that should have aliquots (e.g. `COHNSSER3-R HIV UNINFECTED`).
- [ ] The right-hand grid renders and shows at least one occupied (blue) cell.

---

## Step 5 — Verify Participant and Sample data is intact

- [ ] Navigate to **Participants tab**.
- [ ] All 10 participants from the dummy file still appear.
- [ ] Navigate to **Samples tab** → select a participant.
- [ ] Samples and aliquots still exist.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| `SampleAliquots: 0` after migration | Script deleted SampleAliquot — check deletion order |
| Script fails with IntegrityError | FK constraint on deletion — reorder deletes (AliquotLocation before BoxPosition before StorageBox) |
| Level-2 nodes still show container names after reimport | The fixed import service wasn't deployed — ensure branch is merged to main |
| `Nothing to migrate` on first run | DB path mismatch — check `DB_PATH` in `app/config.py` |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §15 changelog updated.
- [ ] `specs/TODO.md` item struck.
