# Validation — Storage Hierarchy Fix

**Method:** Unit test + manual smoke test  
**Test file:** `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`  
**Gate:** Both automated tests AND manual checks must pass before merging

---

## Unit Tests (`tests/unit/test_storage_hierarchy.py`)

### UT-1 — Upright freezer: box named from container, compartment from shelf

```python
def test_upright_box_named_from_container(session):
    svc = ExcelImportService(session)
    _, comp, rack, drawer, box = svc._get_or_create_storage_hierarchy(
        "TEST-FREEZER", "MY-BOX-CONTAINER", "III", "D-02"
    )
    assert box.name == "MY-BOX-CONTAINER"   # was "Box-1"
    assert comp.name == "III"               # was container_name
    assert rack.name == "D"
    assert drawer.name == "02"
```

### UT-2 — Upright freezer: box named "Box-1" must NOT exist

```python
def test_no_box1_created(session):
    svc = ExcelImportService(session)
    _, _, _, drawer, box = svc._get_or_create_storage_hierarchy(
        "TEST-FREEZER", "REAL-BOX", "I", "A-01"
    )
    assert box.name != "Box-1"
    child_names = [b.name for b in drawer.child_boxes]
    assert "Box-1" not in child_names
```

### UT-3 — Cylindrical freezer: no shelf, sentinel compartment

```python
def test_cylindrical_hierarchy(session):
    svc = ExcelImportService(session)
    _, comp, rack, drawer, box = svc._get_or_create_storage_hierarchy_cylindrical(
        "TEST-CYL", "CYL-BOX", "07"
    )
    assert comp.name == "CYLINDRICAL"
    assert rack.name == "07"
    assert drawer.name == "01"   # sentinel drawer
    assert box.name == "CYL-BOX"
```

### UT-4 — Idempotent: calling twice returns same box object

```python
def test_idempotent_upright(session):
    svc = ExcelImportService(session)
    _, _, _, _, box1 = svc._get_or_create_storage_hierarchy(
        "TEST-FREEZER", "BOX-A", "II", "B-03"
    )
    _, _, _, _, box2 = svc._get_or_create_storage_hierarchy(
        "TEST-FREEZER", "BOX-A", "II", "B-03"
    )
    assert box1.id == box2.id
```

---

## Manual Smoke Test

### SC-1 — Clear and reimport

- [ ] Clear the test DB (or use a fresh study).
- [ ] Go to Participants tab → Import from Excel.
- [ ] Select `/Users/manojgosavi/Downloads/CBMS_Dummy_Data.xlsx`.
- [ ] Import completes without validation errors related to storage.

### SC-2 — Storage tab: Shelf labels at level 2

- [ ] Open Storage tab.
- [ ] Expand a freezer node (e.g. `NARI/COHRPICA/18-19/01 REGULAR`).
- [ ] Level-2 nodes show Roman numeral shelf names: `I`, `II`, `III`, `IV` — **not** box names like `COHNSSER3-R HIV UNINFECTED`.

### SC-3 — Storage tab: Box names at level 5

- [ ] Drill down: Freezer → Shelf → Rack → Drawer.
- [ ] Level-5 Box nodes show the Container name from the Excel file (e.g. `COHNSSER3-R HIV UNINFECTED`).
- [ ] No node named `Box-1` anywhere in the tree.

### SC-4 — "+ Shelf" button label

- [ ] Storage tab toolbar shows button labelled **"＋ Shelf"** (not "＋ Compartment").

### SC-5 — Box grid still works

- [ ] Click a Box node in the tree.
- [ ] Box grid renders correctly on the right panel with the aliquot positions.
- [ ] Aliquot tooltip shows correct Freezer / Shelf / Rack / Drawer / Box names.

### SC-6 — "Shelf deleted successfully" message

- [ ] Select a Shelf node → click Delete → confirm.
- [ ] Success message says "Shelf deleted successfully." (not "Compartment deleted").

### SC-7 — Dummy data storage cross-check

From `CBMS_Dummy_Data.xlsx` row 1:
- Freezer: `NARI/COHRPICA/18-19/01 REGULAR`
- Container: `COHNSSER3-R HIV UNINFECTED`
- Slot Position: `29`
- Shelf: `III`
- Rack: `D-02`

Expected in Storage tab after import:
- [ ] Freezer `NARI/COHRPICA/18-19/01 REGULAR`
  - [ ] Shelf `III`
    - [ ] Rack `D`
      - [ ] Drawer `02`
        - [ ] Box `COHNSSER3-R HIV UNINFECTED`
          - [ ] Position A9 occupied (slot 29 → row 2, col 8 → C3... verify via `_convert_position_number_to_format(29)`)

### SC-8 — Existing functionality unaffected

- [ ] Participant tab still shows participants correctly.
- [ ] Sample tab still shows samples and visit codes.
- [ ] Search tab still finds aliquots with storage location.
- [ ] Block and Ship actions still work.

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---|---|
| Level 2 still shows container names | `_get_or_create_storage_hierarchy` still passes `container_name` to `Compartment()` |
| Box nodes still named "Box-1" | Old `VALID_BOXES` loop or hardcoded "Box-1" fallback still present |
| Cylindrical rows fail validation | `has_storage` check still requires `shelf_name` for all rows |
| Unit tests fail with "no attribute" | `_get_or_create_storage_hierarchy_cylindrical` not added or named differently |
| "+ Compartment" button still visible | `storage_tab.py` button label not updated |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §15 changelog updated.
- [ ] `specs/TODO.md` item struck.
