# Plan: Search Tab — Add Visit Code & Population Columns, Remove Vol

> Status: DRAFT — pending column order confirmation

---

## Step 1 — Extend `SearchResult` in `search_service.py`

Add two new fields to the dataclass:
```python
@dataclass
class SearchResult:
    ...
    visit_code:  Optional[str]   # Sample.visit_code  ← NEW
    population:  Optional[str]   # Participant.population  ← NEW
    volume_ul:   Optional[float] # kept in dataclass, not displayed
    ...
```

Populate in `search()`:
```python
results.append(SearchResult(
    ...
    visit_code=sample.visit_code,
    population=participant.population,
    ...
))
```

No query changes needed — `Participant` and `Sample` are already joined.

---

## Step 2 — Update `COLUMNS` in `search_tab.py`

Proposed column order (20 total → 20 total, net zero change since -1 Vol +2 new):
```
"PID", "Age", "Gender", "Disease", "Cohort", "Population", "Site",
"Sample ID", "Sample Type", "Collection Date", "Visit Code",
"Aliquot ID", "Status",
"Freezer", "Compartment", "Rack", "Drawer", "Box", "Position",
"Discrepancy"
```
- **Population** placed after Cohort (same participant demographic grouping).
- **Visit Code** placed after Collection Date (same sample grouping).
- **Vol (µL)** removed.

---

## Step 3 — Update `values` list in `_on_search()`

```python
values = [
    r.pid, r.age, r.gender, r.disease, r.cohort, r.population, r.site_name,   # 0-6
    r.sample_id, r.sample_type,                                                  # 7-8
    str(r.collection_date) if r.collection_date else "", r.visit_code,           # 9-10
    r.aliquot_id, status,                                                         # 11-12
    r.freezer_name, r.compartment_name, r.rack_name,                             # 13-15
    r.drawer_name, r.box_name, pos_label,                                         # 16-18
    "⚠" if r.discrepancy_remark else "",                                          # 19
]
```

---

## Step 4 — Fix Stretch resize index

Old: `header.setSectionResizeMode(18, QHeaderView.ResizeMode.Stretch)` (Discrepancy was col 18)
New: Discrepancy is at col 19 → update to `19`.

---

## Risk / Notes
- `volume_ul` stays in `SearchResult` dataclass so the export dialog is unaffected.
- Column index shift: `_selected_aliquot_ids()` reads `UserRole` from col 0 (PID) — unchanged.
- Exact positions of Visit Code and Population TBD per user confirmation.
