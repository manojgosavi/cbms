# Requirements — Dashboard: Cohort Flowchart

**Source:** `specs/TODO.md` — Dashboard flowchart item  
**Branch:** `feature/dashboard-flowchart`  
**Date:** 2026-05-11  
**Reference image:** `/Users/manojgosavi/Downloads/FlowChart.jpeg`  
**Status:** Approved

---

## Problem

The Dashboard tab currently shows 4 matplotlib charts (sample types bar, age histogram, aliquot status pie, participants per study bar). The required output is a **cohort flowchart** — a structured grid showing, for each cohort × visit × sample type, how many participants and vials exist. This is the primary summary view biorepository staff and researchers need to assess inventory at a glance.

## Scope

**In scope:**
- Remove the 4 matplotlib charts and the NavigationToolbar from the dashboard. Keep the 6 KPI cards at the top (Participants, Samples, Aliquots, Available, Blocked, Shipped).
- Replace the chart area with a **scrollable horizontal layout** of cohort blocks rendered as `QGroupBox` + `QTableWidget`.
- Keep matplotlib as a dependency (it is in requirements.txt) — just stop using it in this tab.

**Out of scope:**
- Any changes to the KPI strip logic.
- Changes to any other tab.
- Exporting the flowchart to PDF/Excel.

---

## Flowchart Structure (from reference image)

The chart has **4 cohort sections** laid out left to right:

| Cohort Block              | CohortName in DB          | Visit columns   | Population sub-groups |
|---------------------------|---------------------------|-----------------|------------------------|
| Cohort of Adult PLHIV     | `HIV INFECTED-ADULT`      | S · E · F       | None                  |
| Cohort of CLHIV           | `HIV INFECTED-PEDIATRIC`  | E · F           | None                  |
| Cohort of Early HIV (F<1y)| `EARLY HIV INFECTED`      | E · F           | None                  |
| HIV Negative At Risk      | `HIV UNINFECTED`          | S · E · F each  | FSW · PWID · MSM      |

Visit abbreviations:
- **S** = Screening (`Sample.visit_name == "Screening"`)
- **E** = Enrollment (`Sample.visit_name == "Enrollment"`)
- **F** = Follow-up (`Sample.visit_name == "Follow-up"`)

For **HIV UNINFECTED** only, columns are split by population sub-group (FSW, PWID, MSM) from `Participant.population`. Each sub-group has its own S/E/F columns.

---

## Data Model

Each cell in the table contains two values:
1. **n = participant count** — distinct participant IDs for that cohort × visit × [population sub-group]
2. **Vial count per sample type** — number of aliquots for that group

Row order within each QTableWidget:
```
Row 0: n = XX  (participant count header row)
Row 1: Serum
Row 2: ED Plasma
Row 3: HEP Plasma
Row 4: EDTA PBMC
```

---

## Data Query

A single query groups by `cohort_name × population × visit_name × sample_type`:

```python
from sqlalchemy import func

rows = (
    session.query(
        Participant.cohort_name,
        Participant.population,
        Sample.visit_name,
        Sample.sample_type,
        func.count(func.distinct(Participant.id)).label("n_part"),
        func.count(SampleAliquot.id).label("n_vials"),
    )
    .join(Sample,       Sample.participant_id == Participant.id)
    .join(SampleAliquot, SampleAliquot.sample_id == Sample.id)
    .group_by(
        Participant.cohort_name,
        Participant.population,
        Sample.visit_name,
        Sample.sample_type,
    )
    .all()
)
```

This returns all data needed for the flowchart in one DB round-trip. The tab reshapes this into a nested dict before populating the tables:

```python
data[cohort_name][population][visit_name][sample_type] = (n_part, n_vials)
```

For non-UNINFECTED cohorts `population` is ignored (set to a single key `"_all"`).

---

## UI Layout

```
[Study filter]  [Refresh]
[KPI strip: 6 cards]
──────────────────────────────────────────
QScrollArea (horizontal scroll)
  QWidget > QHBoxLayout
    ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐ ┌──────────────────────────────────────┐
    │ Adult PLHIV     │ │ CLHIV         │ │ Early HIV (F<1y)│ │ HIV Negative At Risk Persons          │
    │ QTableWidget    │ │ QTableWidget  │ │ QTableWidget    │ │ QHBoxLayout                           │
    │ cols: S  E  F   │ │ cols: E  F    │ │ cols: E  F      │ │ ┌─────┐ ┌──────┐ ┌─────┐            │
    │ n=   …  …  …   │ │ n=  …  …     │ │ n=   …  …      │ │ │ FSW │ │ PWID │ │ MSM │            │
    │ Ser  …  …  …   │ │ Ser …  …     │ │ Ser  …  …      │ │ │S E F│ │S E F │ │S E F│            │
    │ EDP  …  …  …   │ │ EDP …  …     │ │ EDP  …  …      │ │ └─────┘ └──────┘ └─────┘            │
    │ HEP  …  …  …   │ │ HEP …  …     │ │ HEP  …  …      │ └──────────────────────────────────────┘
    │ PBMC …  …  …   │ │ PBM …  …     │ │ PBMC …  …      │
    └─────────────────┘ └───────────────┘ └─────────────────┘
```

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Render method | `QGroupBox` + `QTableWidget` | No extra dependency; scrollable; easy to style |
| Visit filter | Study filter at top applies to all blocks | Consistent with existing KPI behaviour |
| Missing data | Empty cell (no `0`) | Matches reference image style |
| Population sub-groups | FSW, PWID, MSM only | Only groups with meaningful sample volume in the study |
| Row labels | Short abbreviations (Ser, EDP, HEP, PBMC) | Fit narrow columns |
| Visit order | S → E → F (Screening first) | Chronological visit order |

---

## Context

- `dashboard_service.py` already exists but only has KPI methods. Add `get_flowchart_data()` there.
- `matplotlib` import and `FigureCanvas` can be fully removed from `dashboard_tab.py`.
- The `_has_matplotlib` flag and the fallback label can also be removed.
- The `_draw_charts()` method is replaced by `_draw_flowchart()`.
