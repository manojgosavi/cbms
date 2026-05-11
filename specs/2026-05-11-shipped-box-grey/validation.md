# Validation — Storage Tab: Shipped Cells Turn Grey

**Method:** Manual smoke test  
**Gate:** All checks must pass before merging to `main`

---

## Pre-conditions

- [ ] App runs from source (`python main.py`).
- [ ] At least one storage box exists with at least one aliquot placed in it.
- [ ] The aliquot to be shipped is **blocked** (blocking is required before shipping).

---

## Smoke Test Checklist

### SC-1 — Baseline: occupied cell is blue before shipping

- [ ] Open Storage tab, navigate to a box that has an aliquot placed.
- [ ] Confirm the occupied cell renders **blue**.
- [ ] Click the cell — Move and Remove buttons are **enabled**.

### SC-2 — Ship the aliquot

- [ ] Go to Shipments tab → Create a new shipment.
- [ ] Add the blocked aliquot from SC-1 to the shipment.
- [ ] Complete the shipment form and confirm.
- [ ] Shipment is created with no error.

### SC-3 — Cell turns grey in the box grid

- [ ] Return to Storage tab.
- [ ] Navigate to the same box.
- [ ] The previously blue cell is now **grey** (`#A0A0A0`).
- [ ] The cell is **not** white/empty.

### SC-4 — Tooltip shows SHIPPED status

- [ ] Hover over the grey cell.
- [ ] Tooltip contains `✈ SHIPPED`.
- [ ] Tooltip still shows Aliquot ID, Sample ID, PID.

### SC-5 — Move and Remove are disabled for shipped cells

- [ ] Click the grey cell.
- [ ] Cell info panel appears with the aliquot details.
- [ ] **Move** button is **disabled**.
- [ ] **Remove** button is **disabled**.
- [ ] **Place** button is **disabled** (was already the case for occupied cells).

### SC-6 — Non-shipped occupied cell is unaffected

- [ ] Find a different aliquot in the same or another box that has NOT been shipped.
- [ ] Its cell is still **blue**.
- [ ] Click it — Move and Remove are **enabled**.

### SC-7 — Occupied count in tree still includes shipped cells

- [ ] In the left-hand hierarchy tree, note the `[occupied/total]` count on the box.
- [ ] After shipping, the occupied count is unchanged (shipped position is still recorded).

### SC-8 — App restart persists the grey cell

- [ ] Close and reopen the app.
- [ ] Navigate back to the same box.
- [ ] The shipped cell is still **grey** (confirms `AliquotLocation` was not deleted from the DB).

---

## Failure Criteria (do not merge if any occur)

| Symptom | Likely cause |
|---------|--------------|
| Cell is still white after shipment | `session.delete(loc)` was not removed — check shipment_service.py |
| `ImportError` on `AliquotLocation` | Import was removed but still needed elsewhere — check other usages |
| Move/Remove still enabled on grey cell | `cell.is_shipped` check not added to `_on_cell_clicked` |
| Grey cell disappears after app restart | AliquotLocation is still being deleted — recheck the service |
| Unshipped cells lose Move/Remove | Logic error in the `if cell.is_shipped` branch — verify the else branch enables them |

---

## Post-merge checklist

- [ ] `specs/constitution.md` §9.4: remove `(TODO — not yet implemented)` from Shipped row.
- [ ] `specs/constitution.md` §14: mark G3 `Resolved 2026-05-11`.
- [ ] `TODO.md`: strike the shipped-box grey item.
