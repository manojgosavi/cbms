# Requirements — UI Polish: Box Grid Font & Column Widths

**Source:** `specs/TODO.md` — box grid font + column width items  
**Branch:** `feature/ui-polish-font-columns`  
**Date:** 2026-05-11  
**Status:** Approved

---

## Problem 1 — Box Grid Font Overflow

`BoxGridWidget.paintEvent` draws the aliquot label (PID) at a fixed `10pt bold` font inside an 80×80px cell with 4px padding (inner width = 72px). A PID like `COH20N01A2001S` (14 chars) overflows the cell boundary because `QPainter.drawText()` with `AlignCenter` does not clip — it simply renders beyond the rect.

**Fix:** Auto-scale the font point size down (10 → 8 → 7 → 6pt) until the text fits the inner cell width. If it still overflows at the minimum size, use `QFontMetrics.elidedText()` to append `…`.

---

## Problem 2 — Column Widths Too Large

Several tabs have `setSectionResizeMode(2, Stretch)` or apply `ResizeToContents` only to a small subset of columns, leaving others at Qt's default width (which expands to fill available space). The Participant tab is worst: column 2 (Age) has `Stretch`, making it enormous.

**Fix:** For each `QTableWidget` / `QTreeWidget` table:
1. Apply `ResizeToContents` globally to all columns.
2. Override the **one** long-text column with `Stretch` so it absorbs leftover space.

### Column-by-column plan

| Tab | Current | After fix |
|-----|---------|-----------|
| **Participant** | `ResizeToContents` on 0,1; `Stretch` on 2 (Age) | `ResizeToContents` all; `Stretch` on 9 (Notes) |
| **Search** | `ResizeToContents` all; `Stretch` on 6 (Sample ID) | `ResizeToContents` all; `Stretch` on 18 (Discrepancy) |
| **Sample tree** | `ResizeToContents` on 0,1,2; `Stretch` on 5 (Discrepancy) | No change — already correct |
| **Shipment** | `ResizeToContents` all; `Stretch` on 1 (Recipient) | No change — already correct |
| **Admin users** | `ResizeToContents` all; `Stretch` on 1 (Username) | No change — already correct |
| **Admin audit** | `ResizeToContents` all; `Stretch` on 5 (Description) | No change — already correct |
| **Catalogue** | `ResizeToContents` all | No change — already correct |

Only **Participant** and **Search** tabs need changes.

---

## Scope

**In scope:**
- `app/ui/widgets/box_grid_widget.py` — font auto-scaling in `paintEvent`.
- `app/ui/views/participant_tab.py` — column resize modes.
- `app/ui/views/search_tab.py` — column resize modes.

**Out of scope:**
- Any data or service changes.
- Any other visual change beyond font and column widths.

---

## Context

- `BoxGridWidget.CELL_SIZE = 80`, `CELL_PADDING = 4` → inner width = 72px per axis.
- `QFontMetrics(font).horizontalAdvance(text)` gives the pixel width of `text` at the given font.
- Minimum font size floor: `6pt` — below this PID characters become illegible.
- `ResizeToContents` measures the current data in the model; it must be called after the table is populated (PyQt6 handles this automatically for the header mode).
- Participant tab `COLUMNS` has 11 entries (index 0–10): Notes is at index 9, Registered at 10. Notes is the correct Stretch candidate (free text).
- Search tab `COLUMNS` has 19 entries (index 0–18). Discrepancy (index 18) is the best Stretch candidate — it is the last column and holds variable-length text.
