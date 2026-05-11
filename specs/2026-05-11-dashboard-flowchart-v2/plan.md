# Plan — Dashboard Flowchart v2

**Branch:** `feature/dashboard-flowchart-v2`  
**Estimated effort:** 3–4 hours  
**Files changed:** 1 (`app/ui/views/dashboard_tab.py`)

---

## Task Group 1 — Define data classes at module level

At the top of `dashboard_tab.py`, add two dataclasses (no new imports beyond `dataclasses`):

```python
from dataclasses import dataclass, field

@dataclass
class ColumnSpec:
    visit_label: str          # "S", "E", "F"
    group_label: Optional[str]  # "FSW" / "PWID" / "MSM" / None
    n_participants: int
    sample_counts: dict       # {sample_type_key: vial_count}

@dataclass
class FlowchartSpec:
    cohort_label: str
    columns: list
    has_group_headers: bool = False
```

---

## Task Group 2 — Build CohortFlowchartWidget (QPainter)

Add a new inner class (or module-level class) in `dashboard_tab.py`:

```python
class CohortFlowchartWidget(QWidget):
    LABEL_W    = 110
    COL_W      = 80
    HEADER_H   = 48
    GROUP_HDR_H = 30
    VISIT_HDR_H = 52
    ROW_H      = 30
    MARGIN     = 16

    # Colors
    C_COHORT_BG   = QColor("#1F4E79")
    C_COHORT_FG   = QColor("#FFFFFF")
    C_GROUP_BG    = QColor("#2E75B6")
    C_GROUP_FG    = QColor("#FFFFFF")
    C_VISIT_BG    = QColor("#BDD7EE")
    C_VISIT_FG    = QColor("#1F4E79")
    C_N_BG        = QColor("#D9E1F2")
    C_N_FG        = QColor("#1F4E79")
    C_LABEL_BG    = QColor("#F2F2F2")
    C_VIAL_BG     = QColor("#E2EFDA")
    C_EMPTY_BG    = QColor("#FFFFFF")
    C_GRID        = QColor("#AAAAAA")
    C_TEXT        = QColor("#333333")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec: Optional[FlowchartSpec] = None

    def load(self, spec: FlowchartSpec):
        self._spec = spec
        self._recalculate_size()
        self.update()

    def _recalculate_size(self):
        if not self._spec:
            return
        n_cols = len(self._spec.columns)
        total_h = (
            self.MARGIN
            + self.HEADER_H
            + (self.GROUP_HDR_H if self._spec.has_group_headers else 0)
            + self.VISIT_HDR_H
            + len(SAMPLE_ROWS) * self.ROW_H
            + self.MARGIN
        )
        total_w = self.MARGIN + self.LABEL_W + n_cols * self.COL_W + self.MARGIN
        self.setMinimumSize(total_w, total_h)

    def paintEvent(self, event):
        if not self._spec:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._paint(painter)
        painter.end()

    def _paint(self, painter: QPainter):
        spec = self._spec
        m = self.MARGIN
        n_cols = len(spec.columns)
        total_w = self.LABEL_W + n_cols * self.COL_W

        y = m

        # 1. Cohort header banner
        self._fill_rect(painter, m, y, total_w, self.HEADER_H, self.C_COHORT_BG)
        self._draw_text(painter, m, y, total_w, self.HEADER_H,
                        spec.cohort_label, self.C_COHORT_FG, bold=True, size=14)
        y += self.HEADER_H

        # 2. Population group headers (HIV UNINFECTED only)
        if spec.has_group_headers:
            groups = []
            i = 0
            while i < n_cols:
                grp = spec.columns[i].group_label or ""
                span = sum(1 for c in spec.columns[i:] if c.group_label == grp)
                groups.append((grp, span))
                i += span

            x = m + self.LABEL_W
            self._fill_rect(painter, m, y, self.LABEL_W, self.GROUP_HDR_H, self.C_LABEL_BG)
            for grp_label, span in groups:
                w = span * self.COL_W
                self._fill_rect(painter, x, y, w, self.GROUP_HDR_H, self.C_GROUP_BG)
                self._draw_text(painter, x, y, w, self.GROUP_HDR_H,
                                grp_label, self.C_GROUP_FG, bold=True, size=11)
                self._draw_border(painter, x, y, w, self.GROUP_HDR_H)
                x += w
            y += self.GROUP_HDR_H

        # 3. Visit header + n= row (combined)
        x = m
        self._fill_rect(painter, x, y, self.LABEL_W, self.VISIT_HDR_H, self.C_LABEL_BG)
        self._draw_text(painter, x, y, self.LABEL_W, self.VISIT_HDR_H // 2,
                        "Visit", self.C_VISIT_FG, bold=False, size=9)
        self._draw_text(painter, x, y + self.VISIT_HDR_H // 2,
                        self.LABEL_W, self.VISIT_HDR_H // 2,
                        "n =", self.C_N_FG, bold=True, size=9)
        x += self.LABEL_W
        for col in spec.columns:
            self._fill_rect(painter, x, y, self.COL_W, self.VISIT_HDR_H // 2, self.C_VISIT_BG)
            self._draw_text(painter, x, y, self.COL_W, self.VISIT_HDR_H // 2,
                            col.visit_label, self.C_VISIT_FG, bold=True, size=13)
            self._draw_border(painter, x, y, self.COL_W, self.VISIT_HDR_H // 2)

            self._fill_rect(painter, x, y + self.VISIT_HDR_H // 2,
                            self.COL_W, self.VISIT_HDR_H // 2, self.C_N_BG)
            n_text = str(col.n_participants) if col.n_participants else "—"
            self._draw_text(painter, x, y + self.VISIT_HDR_H // 2,
                            self.COL_W, self.VISIT_HDR_H // 2,
                            n_text, self.C_N_FG, bold=True, size=11)
            self._draw_border(painter, x, y + self.VISIT_HDR_H // 2,
                              self.COL_W, self.VISIT_HDR_H // 2)
            x += self.COL_W
        y += self.VISIT_HDR_H

        # 4. Sample type rows
        for stype_key, stype_label in SAMPLE_ROWS:
            x = m
            self._fill_rect(painter, x, y, self.LABEL_W, self.ROW_H, self.C_LABEL_BG)
            self._draw_text(painter, x, y, self.LABEL_W, self.ROW_H,
                            stype_label, self.C_TEXT, bold=False, size=10, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, padding=6)
            self._draw_border(painter, x, y, self.LABEL_W, self.ROW_H)
            x += self.LABEL_W

            for col in spec.columns:
                count = col.sample_counts.get(stype_key, 0)
                bg = self.C_VIAL_BG if count else self.C_EMPTY_BG
                self._fill_rect(painter, x, y, self.COL_W, self.ROW_H, bg)
                if count:
                    self._draw_text(painter, x, y, self.COL_W, self.ROW_H,
                                    str(count), self.C_TEXT, bold=False, size=11)
                self._draw_border(painter, x, y, self.COL_W, self.ROW_H)
                x += self.COL_W
            y += self.ROW_H

    def _fill_rect(self, p, x, y, w, h, color):
        p.fillRect(x, y, w, h, QBrush(color))

    def _draw_border(self, p, x, y, w, h):
        p.setPen(QPen(self.C_GRID, 1))
        p.drawRect(x, y, w, h)

    def _draw_text(self, p, x, y, w, h, text, color,
                   bold=False, size=10,
                   align=Qt.AlignmentFlag.AlignCenter,
                   padding=0):
        font = QFont()
        font.setBold(bold)
        font.setPointSize(size)
        p.setFont(font)
        p.setPen(QPen(color))
        rect = QRect(x + padding, y, w - padding * 2, h)
        p.drawText(rect, int(align), text)
```

---

## Task Group 3 — Build _build_flowchart_spec() in DashboardTab

Convert `get_flowchart_data()` output into a `FlowchartSpec` for the selected cohort:

```python
def _build_flowchart_spec(self, cohort_key: str, data: dict) -> FlowchartSpec:
    cohort_map = {c[0]: (c[1], c[2]) for c in COHORT_ORDER}
    label, visits = cohort_map[cohort_key]
    cohort_data = data.get(cohort_key, {})

    columns = []
    is_uninfected = cohort_key == "HIV UNINFECTED"

    if is_uninfected:
        for pop in POP_ORDER:
            pop_data = cohort_data.get(pop, {})
            for visit in visits:
                visit_data = pop_data.get(visit, {})
                n = max((v[0] for v in visit_data.values()), default=0)
                counts = {k: v[1] for k, v in visit_data.items()}
                columns.append(ColumnSpec(
                    visit_label=VISIT_SHORT[visit],
                    group_label=pop,
                    n_participants=n,
                    sample_counts=counts,
                ))
    else:
        pop_data = cohort_data.get("_all", {})
        for visit in visits:
            visit_data = pop_data.get(visit, {})
            n = max((v[0] for v in visit_data.values()), default=0)
            counts = {k: v[1] for k, v in visit_data.items()}
            columns.append(ColumnSpec(
                visit_label=VISIT_SHORT[visit],
                group_label=None,
                n_participants=n,
                sample_counts=counts,
            ))

    return FlowchartSpec(
        cohort_label=label,
        columns=columns,
        has_group_headers=is_uninfected,
    )
```

---

## Task Group 4 — Update _build_ui() in DashboardTab

4.1 Remove the `QScrollArea` + `_flow_container` + `_flow_layout` from v1.

4.2 Add the cohort selector row below the KPI strip:

```python
cohort_row = QHBoxLayout()
cohort_row.addStretch()
cohort_row.addWidget(QLabel("Cohort:"))
self._cohort_combo = QComboBox()
for cohort_key, cohort_label, _ in COHORT_ORDER:
    self._cohort_combo.addItem(cohort_label, cohort_key)
self._cohort_combo.currentIndexChanged.connect(self._on_cohort_changed)
cohort_row.addWidget(self._cohort_combo)
layout.addLayout(cohort_row)
```

4.3 Add the `CohortFlowchartWidget` inside a `QScrollArea`:

```python
self._flowchart = CohortFlowchartWidget()
flow_scroll = QScrollArea()
flow_scroll.setWidget(self._flowchart)
flow_scroll.setWidgetResizable(False)
layout.addWidget(flow_scroll)
```

---

## Task Group 5 — Wire refresh and cohort change

```python
def refresh(self):
    study_id = self._study_filter.currentData()
    self._load_kpis(study_id)
    self._redraw_flowchart(study_id)

def _on_cohort_changed(self):
    self._redraw_flowchart(self._study_filter.currentData())

def _redraw_flowchart(self, study_id):
    with get_session() as session:
        from app.core.services.dashboard_service import DashboardService
        data = DashboardService(session).get_flowchart_data(study_id)
    cohort_key = self._cohort_combo.currentData()
    spec = self._build_flowchart_spec(cohort_key, data)
    self._flowchart.load(spec)
```

---

## Task Group 6 — Update docs and commit

6.1 Update `specs/constitution.md` §15 changelog.  
6.2 Strike the flowchart redesign item in `specs/TODO.md`.  
6.3 Commit:

```
feat(dashboard): QPainter flowchart v2 — single cohort view with selector

Replaces QTableWidget blocks with a custom-painted CohortFlowchartWidget.
Adds cohort dropdown selector (default: first cohort). Styled to match
the reference biorepository catalogue layout (dark blue header, green vial
cells, light blue visit headers).
```
