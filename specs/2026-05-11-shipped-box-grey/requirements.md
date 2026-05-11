# Requirements — Storage Tab: Shipped Cells Turn Grey

**Gap ID:** G3  
**Branch:** `feature/shipped-box-grey`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem

When an aliquot is shipped, `ShipmentService.create_shipment()` deletes the `AliquotLocation` record (line 116 of `shipment_service.py`). As a result, the box grid sees no location for that cell and renders it white (empty). The `BoxGridWidget` already has full support for grey shipped cells — `COLOR_SHIPPED`, `CellData.is_shipped`, and the correct `paintEvent` branch — but the data never reaches it because the location was removed.

The constitution (§9.4) states shipped cells must render grey. That contract is broken by the deletion.

## Root Cause (one line)

```python
# shipment_service.py line 110–116 — THIS IS THE BUG
if loc:
    self.session.delete(loc)   # ← deletes the location, cell goes white
```

## Scope

**In scope (G3 only):**

1. **`shipment_service.py`** — Remove the `session.delete(loc)` block. `AliquotLocation` is preserved after shipment. The aliquot already has `is_shipped=True`, which the storage tab reads and passes to `CellData.is_shipped`.

2. **`storage_tab.py` `_on_cell_clicked`** — Disable both Move and Remove buttons when the selected cell's aliquot is shipped. A shipped aliquot is physically gone; these actions make no sense on it.

**Out of scope:**
- Any change to `BoxGridWidget` — it is already correct.
- Any change to `_load_box_grid` — it already reads `aliquot.is_shipped`.
- The `place_aliquot` service — a shipped position has an existing `AliquotLocation` with `unique=True` on `position_id`, so the DB constraint already prevents double-placement.
- Changing the `occupied_positions` property — shipped positions remaining "occupied" is intentional (they record history).

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Delete `AliquotLocation` on ship? | **No** — keep it | Preserves history; enables grey rendering; one-line removal |
| Can a shipped position be reused? | No — position stays occupied | Shipped = physically left the freezer; DB `unique` constraint enforces this |
| Move button on shipped cell | **Disabled** | Aliquot is no longer physically present |
| Remove button on shipped cell | **Disabled** | Shipped record is immutable; removing the location would erase shipment history |
| Place button on shipped cell | Already disabled | Driven by `aliquot_id is not None` — no change needed |

---

## Context

- `AliquotLocation` has `aliquot_id` and `position_id` both as `unique=True` foreign keys. Keeping the record does not allow another aliquot to occupy the same position.
- `SampleAliquot.is_shipped = True` and `is_available = False` are still set by the shipment service — only the `session.delete(loc)` call is removed.
- The shipment service docstring says "aliquot is removed from its storage location automatically" — this is the documented intent that is now changed. The docstring must be updated.
- The constitution §9.4 box grid colour table documents `Shipped → Grey` as the intended state.
