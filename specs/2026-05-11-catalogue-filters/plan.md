# Plan — Catalogue Tab: Advanced Filters

**Branch:** `feature/catalogue-filters`  
**Estimated effort:** 1–2 hours  
**Files changed:** 1 (`app/ui/views/reports_tab.py`)

---

## Task Group 1 — Add imports

1.1 In `reports_tab.py`, add `QFormLayout`, `QLineEdit` to the existing `PyQt6.QtWidgets` import block.

1.2 Add an import for the config enums:
```python
from app.config import CohortName, Disease, Gender, Site, SampleType
```

---

## Task Group 2 — Build the "Narrow results" filter panel in _build_ui

2.1 After the existing `filter_box` group box, add a second group box:

```python
narrow_box = QGroupBox("Narrow results")
nl = QVBoxLayout(narrow_box)

row1 = QHBoxLayout()
row2 = QHBoxLayout()

# PID
self._f_pid = QLineEdit()
self._f_pid.setPlaceholderText("partial match")
self._f_pid.setMaximumWidth(140)

# Gender combo
self._f_gender = QComboBox()
self._f_gender.addItem("All genders", None)
for g in Gender:
    self._f_gender.addItem(g.value, g.value)

# Disease
self._f_disease = QLineEdit()
self._f_disease.setPlaceholderText("partial match")
self._f_disease.setMaximumWidth(160)

# Cohort combo
self._f_cohort = QComboBox()
self._f_cohort.addItem("All cohorts", None)
for c in CohortName:
    self._f_cohort.addItem(c.value, c.value)

# Site combo
self._f_site = QComboBox()
self._f_site.addItem("All sites", None)
for s in Site:
    self._f_site.addItem(s.value, s.value)

# Sample Type combo (column filter)
self._f_stype = QComboBox()
self._f_stype.addItem("All sample types", None)
for st in SampleType:
    self._f_stype.addItem(st.value, st.value)

# Clear button
btn_clear = QPushButton("Clear filters")
btn_clear.clicked.connect(self._on_clear_filters)

row1.addWidget(QLabel("PID:"));     row1.addWidget(self._f_pid)
row1.addSpacing(12)
row1.addWidget(QLabel("Gender:"));  row1.addWidget(self._f_gender)
row1.addSpacing(12)
row1.addWidget(QLabel("Disease:")); row1.addWidget(self._f_disease)
row1.addStretch()

row2.addWidget(QLabel("Cohort:"));      row2.addWidget(self._f_cohort)
row2.addSpacing(12)
row2.addWidget(QLabel("Site:"));        row2.addWidget(self._f_site)
row2.addSpacing(12)
row2.addWidget(QLabel("Sample Type:")); row2.addWidget(self._f_stype)
row2.addSpacing(12)
row2.addWidget(btn_clear)
row2.addStretch()

nl.addLayout(row1)
nl.addLayout(row2)
layout.addWidget(narrow_box)
```

---

## Task Group 3 — Apply filters in _on_generate

3.1 After the service call in `_on_generate`, add the filter pass before the "no data" check:

```python
def _on_generate(self):
    study_id = self._study_combo.currentData()
    avail    = self._available_only.isChecked()

    with get_session() as session:
        svc = CatalogueService(session)
        rows, col_headers = svc.generate(study_id=study_id, available_only=avail)

    # ── Post-query filters ─────────────────────────────────────────
    pid_q     = self._f_pid.text().strip().lower()
    gender_q  = self._f_gender.currentData()
    disease_q = self._f_disease.text().strip().lower()
    cohort_q  = self._f_cohort.currentData()
    site_q    = self._f_site.currentData()
    stype_q   = self._f_stype.currentData()

    def _matches(row):
        if pid_q     and pid_q not in row.pid.lower():                 return False
        if gender_q  and row.gender != gender_q:                       return False
        if disease_q and disease_q not in (row.disease or "").lower(): return False
        if cohort_q  and row.cohort_name != cohort_q:                  return False
        if site_q    and row.site_name != site_q:                      return False
        return True

    rows = [r for r in rows if _matches(r)]

    if stype_q:
        col_headers = [c for c in col_headers if c == stype_q]
        for r in rows:
            r.sample_counts = {k: v for k, v in r.sample_counts.items() if k == stype_q}

    self._rows, self._col_headers = rows, col_headers
    # ... rest of existing population logic unchanged
```

3.2 Update the summary label to mention active filters:
```python
filter_note = " [filtered]" if any([pid_q, gender_q, disease_q, cohort_q, site_q, stype_q]) else ""
self._summary_lbl.setText(
    f"{len(self._rows)} participant(s)  |  "
    f"{len(self._col_headers)} sample type(s)  |  "
    f"{total_aliquots} total aliquots{filter_note}"
)
```

---

## Task Group 4 — Add _on_clear_filters method

```python
def _on_clear_filters(self):
    self._f_pid.clear()
    self._f_gender.setCurrentIndex(0)
    self._f_disease.clear()
    self._f_cohort.setCurrentIndex(0)
    self._f_site.setCurrentIndex(0)
    self._f_stype.setCurrentIndex(0)
```

---

## Task Group 5 — Update docs and commit

5.1 Mark G4 resolved in `specs/constitution.md` §14.

5.2 Strike G4 in `TODO.md`.

5.3 Commit:
```
feat(catalogue-tab): add advanced filters for gender, disease, cohort, site, PID, sample type

Resolves G4. Post-query Python filter narrows the pivot table without
changing CatalogueService. Exported Excel reflects the filtered view.
```
