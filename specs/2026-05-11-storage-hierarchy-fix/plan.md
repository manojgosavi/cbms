# Plan — Storage Hierarchy Fix

**Branch:** `feature/storage-hierarchy-fix`  
**Estimated effort:** 2–3 hours  
**Files changed:** 2 (`app/core/services/excel_import_service.py`, `app/ui/views/storage_tab.py`)

---

## Task Group 1 — Fix _get_or_create_storage_hierarchy for upright freezers

In `excel_import_service.py`, rewrite `_get_or_create_storage_hierarchy` with correct column-to-level mapping.

**Signature** (unchanged):
```python
def _get_or_create_storage_hierarchy(
    self, freezer_name: str, container_name: str,
    shelf_name: str, rack_drawer_combined: str
) -> tuple[Freezer, Compartment, StorageRack, StorageDrawer, StorageBox]:
```

**New logic (upright path — shelf_name is present):**
```python
rack_letter, drawer_number = rack_drawer_combined.split('-')

# Freezer (unchanged)
freezer = freezer_repo.get_by_name(freezer_name) or Freezer(name=freezer_name)
...

# Compartment = Shelf (I/II/III/IV) — was container_name, now shelf_name
compartment = next((c for c in freezer.compartments if c.name == shelf_name), None)
if not compartment:
    compartment = Compartment(name=shelf_name, freezer_id=freezer.id)
    ...

# StorageRack = Rack letter (A-F) — unchanged position, name comes from rack_letter
rack = next((r for r in compartment.racks if r.name == rack_letter), None)
...

# StorageDrawer = Drawer number (01-05) — unchanged position, name from drawer_number
drawer = next((d for d in rack.drawers if d.name == drawer_number), None)
...

# StorageBox = container_name (was "Box-1" hardcoded) — THE KEY FIX
box = next((b for b in drawer.boxes if b.name == container_name), None)
if not box:
    box = StorageBox(name=container_name, drawer_id=drawer.id, rows=10, cols=10)
    session.add(box)
    session.flush()
    # Pre-populate grid positions
    for r in range(10):
        for c in range(10):
            session.add(BoxPosition(box_id=box.id, row=r, col=c))
    session.flush()

return freezer, compartment, rack, drawer, box
```

Note: the auto-creation of child levels (shelves under compartment, racks under shelf, etc.) stays identical in structure — only the names passed to the constructors change.

Remove `VALID_BOXES` constant and all references to `"Box-1"`.

---

## Task Group 2 — Add cylindrical freezer path

Add a separate method for cylindrical freezers:

```python
CYLINDRICAL_SENTINEL_COMPARTMENT = "CYLINDRICAL"
CYLINDRICAL_SENTINEL_DRAWER = "01"
VALID_CYLINDRICAL_RACKS = [f"{i:02d}" for i in range(1, 14)]  # "01" ... "13"

def _get_or_create_storage_hierarchy_cylindrical(
    self, freezer_name: str, container_name: str, rack_number: str
) -> tuple[Freezer, Compartment, StorageRack, StorageDrawer, StorageBox]:
    """Hierarchy for cylindrical freezers (no shelf, no drawer)."""
    freezer_repo = FreezerRepository(self.session)

    freezer = freezer_repo.get_by_name(freezer_name) or Freezer(name=freezer_name)
    if not freezer.id:
        self.session.add(freezer)
        self.session.flush()

    # Sentinel compartment
    compartment = next(
        (c for c in freezer.compartments
         if c.name == CYLINDRICAL_SENTINEL_COMPARTMENT), None
    )
    if not compartment:
        compartment = Compartment(
            name=CYLINDRICAL_SENTINEL_COMPARTMENT, freezer_id=freezer.id
        )
        self.session.add(compartment)
        self.session.flush()

    # Rack (01-13)
    rack = next((r for r in compartment.racks if r.name == rack_number), None)
    if not rack:
        rack = StorageRack(name=rack_number, compartment_id=compartment.id)
        self.session.add(rack)
        self.session.flush()

    # Sentinel drawer
    drawer = next((d for d in rack.drawers if d.name == CYLINDRICAL_SENTINEL_DRAWER), None)
    if not drawer:
        drawer = StorageDrawer(name=CYLINDRICAL_SENTINEL_DRAWER, rack_id=rack.id)
        self.session.add(drawer)
        self.session.flush()

    # Box = container_name
    box = next((b for b in drawer.boxes if b.name == container_name), None)
    if not box:
        box = StorageBox(name=container_name, drawer_id=drawer.id, rows=10, cols=10)
        self.session.add(box)
        self.session.flush()
        for r in range(10):
            for c in range(10):
                self.session.add(BoxPosition(box_id=box.id, row=r, col=c))
        self.session.flush()

    return freezer, compartment, rack, drawer, box
```

---

## Task Group 3 — Update validation for cylindrical rows

In `_validate_row`, split storage validation into upright vs cylindrical:

```python
storage_fields_core = [row.freezer_name, row.container_name, row.slot_position]
is_cylindrical = bool(storage_fields_core and not row.shelf_name)
has_storage = any([row.freezer_name, row.container_name, row.shelf_name,
                   row.rack_drawer_combined, row.slot_position])

if has_storage:
    if not all(storage_fields_core):
        # freezer, container, slot are always required
        ...missing field errors...
    elif is_cylindrical:
        # Cylindrical path: validate rack_drawer_combined is a plain number 01-13
        rack_str = str(row.rack_drawer_combined).strip().zfill(2)
        if rack_str not in VALID_CYLINDRICAL_RACKS:
            errors.append(f"Cylindrical rack must be 01-13, got '{rack_str}'")
        else:
            row.rack_drawer_combined = rack_str  # normalize to "01" format
    else:
        # Upright path: existing shelf + rack-drawer validation (unchanged)
        ...existing upright validation...
```

---

## Task Group 4 — Update import_rows to dispatch to correct hierarchy method

In `import_rows`, replace the single `_get_or_create_storage_hierarchy` call with:

```python
if row.freezer_name:
    is_cylindrical = not row.shelf_name
    if is_cylindrical:
        freezer, compartment, rack, drawer, box = \
            self._get_or_create_storage_hierarchy_cylindrical(
                row.freezer_name, row.container_name, row.rack_drawer_combined
            )
    else:
        freezer, compartment, rack, drawer, box = \
            self._get_or_create_storage_hierarchy(
                row.freezer_name, row.container_name,
                row.shelf_name, row.rack_drawer_combined
            )
    # place aliquot in box grid (unchanged)
    ...
```

Also remove all `print(f"[DEBUG] ...")` statements from `import_rows`.

---

## Task Group 5 — UI label changes in storage_tab.py

5.1 Change the tree node prefix for compartments:

```python
# Before
comp_item.setText(0, f"🔲  {comp_name}")
# After
comp_item.setText(0, f"📋  {comp_name}")
```

5.2 Change the "+ Compartment" button label:

```python
# Before
btn_new_compartment = QPushButton("＋ Compartment")
# After
btn_new_compartment = QPushButton("＋ Shelf")
```

5.3 Update the success message in `_on_delete_item`:

```python
# Before
QMessageBox.information(self, "Success", f"{item_type.capitalize()} deleted successfully.")
# After — map internal type to display name
TYPE_LABELS = {"freezer": "Freezer", "compartment": "Shelf",
               "rack": "Rack", "drawer": "Drawer", "box": "Box"}
label = TYPE_LABELS.get(item_type, item_type.capitalize())
QMessageBox.information(self, "Success", f"{label} deleted successfully.")
```

---

## Task Group 6 — Write unit test

In `tests/unit/`, add `test_storage_hierarchy.py`:

```python
def test_upright_box_named_from_container():
    """Box must be named from container_name, not 'Box-1'."""
    ...create in-memory session...
    svc = ExcelImportService(session)
    f, comp, rack, drawer, box = svc._get_or_create_storage_hierarchy(
        "FREEZER-1", "MY-BOX-NAME", "III", "D-02"
    )
    assert box.name == "MY-BOX-NAME"
    assert comp.name == "III"   # Compartment = shelf name
    assert rack.name == "D"     # Rack = letter
    assert drawer.name == "02"  # Drawer = number

def test_cylindrical_no_shelf_required():
    """Cylindrical path does not create shelf-level nodes."""
    svc = ExcelImportService(session)
    f, comp, rack, drawer, box = svc._get_or_create_storage_hierarchy_cylindrical(
        "FREEZER-3", "MY-BOX-NAME", "07"
    )
    assert box.name == "MY-BOX-NAME"
    assert comp.name == "CYLINDRICAL"
    assert rack.name == "07"
```

---

## Task Group 7 — Update docs and commit

7.1 Mark item resolved in `specs/TODO.md`.  
7.2 Update `specs/constitution.md` §15 changelog.  
7.3 Commit:

```
fix(excel-import): correct storage hierarchy column mapping

Container (col O) is now the Box name. Shelf (col Q) is now the
Compartment. Removes hardcoded 'Box-1'. Adds cylindrical freezer
path (no shelf/drawer required). Renames Compartment→Shelf in
Storage tab UI labels.
```
