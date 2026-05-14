# UX Improvements — Export, Sortable Columns, Last Backup Indicator

**Date:** 2026-05-14  
**Branch:** feature/ux-improvements  
**Status:** In Progress

---

## Scope

Three independent UX improvements:

### 1. Export from Participant Tab
Add an "Export to Excel" button to the Participant tab toolbar. Exports **all rows matching the current filters** (not just the visible page) to an `.xlsx` file via a Save dialog. Columns match the table: PID, Study, Age, Gender, Population, Disease, Site, Cohort Name, Visit Code, Notes, Registered.

### 2. Sortable Column Headers
Enable `setSortingEnabled(True)` on three tables so clicking a column header sorts rows ascending/descending:
- Participant tab (`QTableWidget`)
- Search results tab (`QTableWidget`)
- Audit Log in Admin tab (`QTableWidget`)

Sorting is disabled during row population and re-enabled after to avoid mid-load sort glitches.

### 3. Last Backup Indicator
Show the timestamp of the most recent backup in two places:
- The **Admin tab** header area (next to the Backup button if one exists, or as a label)
- The **main window status bar** (right side, alongside the logged-in user info)

The indicator is computed by scanning `data/backups/` for the newest `.db` file and reading its modification time. It updates after each backup is taken.

---

## Decisions

| Decision | Choice |
|----------|--------|
| Export scope | All filtered results (re-queries with `page_size=9999`), not just visible page |
| Export format | openpyxl `.xlsx`, same style as Search export |
| Sort persistence | Not persisted across refreshes — table re-sorts on next load |
| Backup scan location | `config.DB_PATH.parent / "backups"` (same path the backup service uses) |
| Backup not found | Show "No backup found" instead of hiding the label |

---

## Out of Scope
- Import summary dialog (not selected)
- Sorting in Sample tab tree or Storage tab tree (QTreeWidget — complex with hierarchy)
- Scheduled automatic backup
