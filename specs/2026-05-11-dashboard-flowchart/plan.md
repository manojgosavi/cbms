# Plan — Dashboard: Cohort Flowchart

**Branch:** `feature/dashboard-flowchart`  
**Estimated effort:** 2–3 hours  
**Files changed:** 2 (`app/core/services/dashboard_service.py`, `app/ui/views/dashboard_tab.py`)

---

## Task Group 1 — Add get_flowchart_data() to dashboard_service.py

1.1 Open `app/core/services/dashboard_service.py`. Add a new method:

```python
def get_flowchart_data(self, study_id=None) -> dict:
    """
    Returns nested dict:
      data[cohort_name][population_key][visit_name][sample_type] = (n_participants, n_vials)
    For non-UNINFECTED cohorts, population_key is always "_all".
    """
    from sqlalchemy import func
    from app.core.models.models import Participant, Sample, SampleAliquot

    q = (
        self.session.query(
            Participant.cohort_name,
            Participant.population,
            Sample.visit_name,
            Sample.sample_type,
            func.count(func.distinct(Participant.id)).label("n_part"),
            func.count(SampleAliquot.id).label("n_vials"),
        )
        .join(Sample,        Sample.participant_id == Participant.id)
        .join(SampleAliquot, SampleAliquot.sample_id == Sample.id)
    )
    if study_id:
        q = q.filter(Participant.study_id == study_id)

    q = q.group_by(
        Participant.cohort_name,
        Participant.population,
        Sample.visit_name,
        Sample.sample_type,
    )

    # Build nested dict
    from collections import defaultdict
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    UNINFECTED = "HIV UNINFECTED"
    POP_GROUPS = {"FSW", "PWID", "MSM"}

    for cohort, population, visit_name, sample_type, n_part, n_vials in q.all():
        if not cohort or not visit_name or not sample_type:
            continue
        if cohort == UNINFECTED:
            pop_key = population if population in POP_GROUPS else "Other"
        else:
            pop_key = "_all"
        data[cohort][pop_key][visit_name][sample_type] = (n_part, n_vials)

    return data
```

---

## Task Group 2 — Rewrite dashboard_tab.py

2.1 Remove all matplotlib-related imports, the `_has_matplotlib` flag, `_draw_charts()`, and the `FigureCanvas` / `NavigationToolbar` setup from `_build_ui()`.

2.2 Add a `QScrollArea` in `_build_ui()` after the KPI strip:

```python
from PyQt6.QtWidgets import QScrollArea, QSizePolicy

# Flowchart scroll area
self._flow_scroll = QScrollArea()
self._flow_scroll.setWidgetResizable(True)
self._flow_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
self._flow_container = QWidget()
self._flow_layout = QHBoxLayout(self._flow_container)
self._flow_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
self._flow_layout.setSpacing(12)
self._flow_scroll.setWidget(self._flow_container)
layout.addWidget(self._flow_scroll)
```

2.3 Replace `_draw_charts()` with `_draw_flowchart(study_id)`:

```python
COHORT_ORDER = [
    ("HIV INFECTED-ADULT",     "Adult PLHIV",          ["Screening", "Enrollment", "Follow-up"]),
    ("HIV INFECTED-PEDIATRIC", "CLHIV",                ["Enrollment", "Follow-up"]),
    ("EARLY HIV INFECTED",     "Early HIV (F < 1 yr)", ["Enrollment", "Follow-up"]),
    ("HIV UNINFECTED",         "HIV Negative At Risk",  ["Screening", "Enrollment", "Follow-up"]),
]
SAMPLE_ROWS = [
    ("Serum",     "Serum"),
    ("ED Plasma", "ED Plasma"),
    ("HEP Plasma","HEP Plasma"),
    ("EDTA PBMC", "EDTA PBMC"),
]
POP_ORDER = ["FSW", "PWID", "MSM"]
VISIT_SHORT = {"Screening": "S", "Enrollment": "E", "Follow-up": "F"}

def _draw_flowchart(self, study_id):
    # Clear previous widgets from flow layout
    while self._flow_layout.count():
        item = self._flow_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    with get_session() as session:
        from app.core.services.dashboard_service import DashboardService
        data = DashboardService(session).get_flowchart_data(study_id)

    for cohort_key, cohort_label, visits in COHORT_ORDER:
        cohort_data = data.get(cohort_key, {})

        outer = QGroupBox(cohort_label)
        outer.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 12px; "
            "border: 2px solid #2E75B6; border-radius: 6px; "
            "margin-top: 10px; padding: 6px; } "
            "QGroupBox::title { color: #2E75B6; subcontrol-origin: margin; left: 8px; }"
        )
        outer_layout = QHBoxLayout(outer)
        outer_layout.setSpacing(6)

        if cohort_key == "HIV UNINFECTED":
            # Sub-group blocks per population
            for pop in POP_ORDER:
                pop_data = cohort_data.get(pop, {})
                pop_box = self._make_cohort_table(pop, pop_data, visits)
                outer_layout.addWidget(pop_box)
        else:
            pop_data = cohort_data.get("_all", {})
            table = self._make_cohort_table(None, pop_data, visits)
            outer_layout.addWidget(table)

        self._flow_layout.addWidget(outer)
```

2.4 Add `_make_cohort_table()` helper:

```python
def _make_cohort_table(self, title, pop_data, visits):
    """Build a QGroupBox with a QTableWidget for one cohort / sub-group."""
    from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
    from PyQt6.QtGui import QColor, QFont

    VISIT_SHORT = {"Screening": "S", "Enrollment": "E", "Follow-up": "F"}
    SAMPLE_ROWS = [
        ("Serum",     "Serum"),
        ("ED Plasma", "ED Plasma"),
        ("HEP Plasma","HEP Plasma"),
        ("EDTA PBMC", "EDTA PBMC"),
    ]

    box = QGroupBox(title or "")
    box.setStyleSheet(
        "QGroupBox { font-size: 11px; font-weight: 600; "
        "border: 1px solid #AAAAAA; border-radius: 4px; margin-top: 8px; } "
        "QGroupBox::title { color: #555; subcontrol-origin: margin; left: 6px; }"
    )
    vl = QVBoxLayout(box)
    vl.setContentsMargins(4, 12, 4, 4)

    n_cols = len(visits)
    n_rows = 1 + len(SAMPLE_ROWS)   # n= row + 4 sample type rows

    tbl = QTableWidget(n_rows, n_cols)
    tbl.setHorizontalHeaderLabels([VISIT_SHORT.get(v, v) for v in visits])
    tbl.setVerticalHeaderLabels(["n ="] + [sr[1] for sr in SAMPLE_ROWS])
    tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    tbl.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tbl.setAlternatingRowColors(True)
    tbl.verticalHeader().setDefaultSectionSize(24)
    tbl.horizontalHeader().setDefaultSectionSize(56)

    bold_font = QFont()
    bold_font.setBold(True)

    for col_idx, visit in enumerate(visits):
        visit_data = pop_data.get(visit, {})

        # n= row — sum distinct participants across sample types for this visit
        n_total = max(
            (v[0] for v in visit_data.values()), default=0
        )
        n_item = QTableWidgetItem(str(n_total) if n_total else "")
        n_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        n_item.setFont(bold_font)
        n_item.setBackground(QColor("#D9E1F2"))
        tbl.setItem(0, col_idx, n_item)

        # Sample type rows
        for row_idx, (stype_key, stype_label) in enumerate(SAMPLE_ROWS, start=1):
            n_part, n_vials = visit_data.get(stype_key, (0, 0))
            val_item = QTableWidgetItem(str(n_vials) if n_vials else "")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if n_vials:
                val_item.setBackground(QColor("#E2EFDA"))
            tbl.setItem(row_idx, col_idx, val_item)

    vl.addWidget(tbl)
    return box
```

---

## Task Group 3 — Wire up refresh()

3.1 Update `refresh()` to call `_draw_flowchart(study_id)` instead of `_draw_charts(study_id)`:

```python
def refresh(self):
    study_id = self._study_filter.currentData()
    self._load_kpis(study_id)
    self._draw_flowchart(study_id)
```

3.2 Remove the `if self._has_matplotlib:` guard — `_draw_flowchart` always runs.

---

## Task Group 4 — Check dashboard_service.py exists and has a session

4.1 Confirm `app/core/services/dashboard_service.py` exists and its class accepts a `Session`. If it only has module-level functions, wrap `get_flowchart_data` accordingly.

---

## Task Group 5 — Update docs and commit

5.1 Add the flowchart feature to `specs/constitution.md` §15 changelog.

5.2 Update `specs/TODO.md` to strike the dashboard item.

5.3 Commit:
```
feat(dashboard): replace matplotlib charts with cohort flowchart

Removes 4-chart matplotlib view. Adds QTableWidget-based cohort
flowchart (Adult PLHIV / CLHIV / Early HIV / HIV-Negative At Risk)
grouped by visit (S/E/F) and sample type. Live data from DB via
DashboardService.get_flowchart_data().
```
