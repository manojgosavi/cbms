# Plan — UI Polish: Box Grid Font & Column Widths

**Branch:** `feature/ui-polish-font-columns`  
**Estimated effort:** 30 minutes  
**Files changed:** 3 (`box_grid_widget.py`, `participant_tab.py`, `search_tab.py`)

---

## Task Group 1 — Box grid: auto-scaling font in paintEvent

In `app/ui/widgets/box_grid_widget.py`, replace the fixed `font_label` draw block with a helper that shrinks the font until the text fits:

```python
# Before (inside paintEvent "Draw cells" loop):
if cell and cell.aliquot_label:
    painter.setFont(font_label)
    ...
    painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, cell.aliquot_label)

# After:
if cell and cell.aliquot_label:
    inner = rect.adjusted(
        self.CELL_PADDING, self.CELL_PADDING,
        -self.CELL_PADDING, -self.CELL_PADDING
    )
    text_color = (COLOR_TEXT_DARK
                  if fill in (COLOR_EMPTY, COLOR_HOVER)
                  else COLOR_TEXT)
    painter.setPen(QPen(text_color))
    self._draw_fitted_label(painter, inner, cell.aliquot_label)
```

Add the helper method to `BoxGridWidget`:

```python
def _draw_fitted_label(self, painter: QPainter, rect: QRect, text: str) -> None:
    """
    Draw text inside rect, shrinking font size until it fits.
    Falls back to elided text at minimum size if still too wide.
    """
    for pt in (10, 8, 7, 6):
        font = QFont()
        font.setPointSize(pt)
        font.setBold(pt >= 8)   # bold only at larger sizes
        fm = QFontMetrics(font)
        if fm.horizontalAdvance(text) <= rect.width():
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            return
    # Minimum size — elide if still overflowing
    font = QFont()
    font.setPointSize(6)
    font.setBold(False)
    painter.setFont(font)
    fm = QFontMetrics(font)
    elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, elided)
```

Add `QFontMetrics` to the existing `from PyQt6.QtGui import ...` import line.

Remove the now-unused `font_label` variable from `paintEvent` (it was only used for cell labels).

---

## Task Group 2 — Participant tab: fix column resize modes

In `app/ui/views/participant_tab.py`, replace the three `setSectionResizeMode` calls in `_build_ui`:

```python
# Before:
header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

# After:
header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)  # all columns
header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)         # Notes column
```

Column 9 is "Notes" in the 11-column layout:
`["PID", "Study", "Age", "Gender", "Population", "Disease", "Site", "Cohort Name", "Visit Code", "Notes", "Registered"]`

---

## Task Group 3 — Search tab: fix column resize modes

In `app/ui/views/search_tab.py`, replace the two `setSectionResizeMode` calls in `_build_ui`:

```python
# Before:
header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

# After:
header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)   # all columns
header.setSectionResizeMode(18, QHeaderView.ResizeMode.Stretch)         # Discrepancy column
```

Column 18 is "Discrepancy" — the last column and most variable in length.

---

## Task Group 4 — Update docs and commit

4.1 Strike both TODO items in `specs/TODO.md`.  
4.2 Add entry to `specs/constitution.md` §15.  
4.3 Commit:

```
fix(ui): auto-scale box grid font to fit cell; fix column widths across tabs

BoxGridWidget: shrink font 10→8→7→6pt until PID fits the cell,
falling back to elidedText at minimum size.
Participant tab: ResizeToContents all columns, Stretch on Notes (9).
Search tab: ResizeToContents all columns, Stretch on Discrepancy (18).
```
