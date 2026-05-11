# Requirements — Dashboard Flowchart v2

**Source:** `specs/TODO.md` — flowchart redesign item  
**Branch:** `feature/dashboard-flowchart-v2`  
**Date:** 2026-05-11  
**Reference image:** `/Users/manojgosavi/Downloads/FlowChart.jpeg`  
**Status:** Approved

---

## Problem

The v1 flowchart used `QTableWidget` inside `QGroupBox` blocks. The result looked like a plain spreadsheet — default grey grid, no hierarchy, cramped headers — far from the reference image's clean card-style layout with bold cohort titles, clear visit columns, and styled count cells.

## Scope

**In scope:**
- Replace all `QTableWidget` blocks with a single **custom `QPainter`-rendered widget** (`CohortFlowchartWidget`) for the selected cohort.
- Add a **cohort selector dropdown** below the KPI strip (right-aligned). The user always sees exactly one cohort at a time. Dropdown entries are the 4 cohort names. Default = first cohort.
- Remove the `QScrollArea` horizontal tiling. The single-cohort view fills the available width.
- Keep all KPI cards, study filter, and refresh button unchanged.
- Keep `DashboardService.get_flowchart_data()` unchanged.

**Out of scope:**
- Multi-cohort overview mode.
- Export to PNG/PDF.
- Any other tab.

---

## Cohort Selector Layout

Below the KPI strip, a single filter row:

```
[  Cohort:  [▼ Cohort of Adult PLHIV        ]  ]   (right-aligned)
```

Options:
1. Cohort of Adult PLHIV  (`HIV INFECTED-ADULT`)
2. Cohort of CLHIV  (`HIV INFECTED-PEDIATRIC`)
3. Cohort of Early HIV (F<1yr)  (`EARLY HIV INFECTED`)
4. HIV Negative At Risk  (`HIV UNINFECTED`)

Changing the selection immediately redraws the flowchart widget (no Refresh needed).

---

## CohortFlowchartWidget — Painted Layout

A `QWidget` subclass that overrides `paintEvent`. Sized dynamically based on data.

### Layout for standard cohorts (Adult PLHIV, CLHIV, Early HIV)

```
┌──────────────────────────────────────────────────────┐  ← HEADER_H (48px)
│  Cohort of Adult PLHIV          (white text on blue) │
├──────────┬──────────┬──────────┬──────────────────────┤  ← VISIT_HDR_H (36px)
│          │    S     │    E     │    F                 │
│          │ n=257    │ n=199    │ n=169                │
├──────────┼──────────┼──────────┼──────────────────────┤  ← N_ROW_H (32px)
│ Serum    │   350    │   269    │   816                │  ← CELL_H (28px) each
│ ED Plasma│   379    │    –     │    –                 │
│ HEP Plasma│  364   │    –     │   867                │
│ EDTA PBMC│   463   │    –     │  1523                │
└──────────┴──────────┴──────────┴──────────────────────┘
```

### Layout for HIV UNINFECTED (two-level column headers)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  HIV Negative At Risk Persons                                            │
├──────────┬──────────────────────┬──────────────────────┬─────────────────┤
│          │         FSW          │        PWID          │      MSM        │
├──────────┼───────┬──────┬───────┼───────┬──────┬───────┼───────┬──────┬──┤
│          │   S   │  E   │   F   │   S   │  E   │   F   │   S   │  E   │ F│
│          │n=312  │n=84  │ n=75  │ n=708 │n=323 │n=279  │  ...  │      │  │
├──────────┼───────┼──────┼───────┼───────┼──────┼───────┼───────┼──────┼──┤
│ Serum    │  668  │  172 │  537  │  997  │  542 │ 1159  │  ...  │      │  │
│ ED Plasma│       │      │       │       │      │       │       │      │  │
│HEP Plasma│       │      │       │       │      │       │       │      │  │
│EDTA PBMC │       │      │       │       │      │       │       │      │  │
└──────────┴───────┴──────┴───────┴───────┴──────┴───────┴───────┴──────┴──┘
```

---

## Color Scheme (matching reference image)

| Element                  | Color           |
|--------------------------|-----------------|
| Cohort header background | `#1F4E79` (dark blue) |
| Cohort header text       | `#FFFFFF` (white) |
| Population group header  | `#2E75B6` (mid blue) |
| Visit header background  | `#BDD7EE` (light blue) |
| n= row background        | `#D9E1F2` (very light blue) |
| n= row text              | `#1F4E79` bold |
| Sample label column      | `#F2F2F2` (light grey) |
| Non-zero vial cell       | `#E2EFDA` (light green) |
| Zero / empty cell        | `#FFFFFF` (white) |
| Grid lines               | `#AAAAAA` |

---

## Data Model passed to the widget

```python
@dataclass
class ColumnSpec:
    visit_label: str        # "S", "E", "F"
    group_label: str | None # "FSW"/"PWID"/"MSM" or None
    n_participants: int
    sample_counts: dict     # {sample_type_key: vial_count}

@dataclass
class FlowchartSpec:
    cohort_label: str
    columns: list[ColumnSpec]
    has_group_headers: bool  # True only for HIV UNINFECTED
```

The `DashboardTab` builds a `FlowchartSpec` from `get_flowchart_data()` and passes it to `CohortFlowchartWidget.load(spec)`.

---

## Dimensions

| Constant      | Value  | Purpose                              |
|---------------|--------|--------------------------------------|
| `LABEL_W`     | 110 px | Sample type label column width       |
| `COL_W`       | 80 px  | Per-visit column width               |
| `HEADER_H`    | 48 px  | Cohort name banner height            |
| `GROUP_HDR_H` | 30 px  | Population group header height (UNINFECTED only) |
| `VISIT_HDR_H` | 52 px  | Visit letter + n= number height      |
| `ROW_H`       | 30 px  | Each sample type row height          |
| `MARGIN`      | 16 px  | Outer padding                        |

---

## Context

- `CohortFlowchartWidget` lives in `app/ui/views/dashboard_tab.py` (no new file needed at this scale).
- The widget calls `self.update()` when `load(spec)` is called — `paintEvent` does all drawing.
- `setMinimumSize()` is called after `load()` so the scroll area knows the content size.
- If no data for a cell, draw an empty white cell (no text).
