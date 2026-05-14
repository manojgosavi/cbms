# Plan — UX Improvements

## Task Group 1 — Export from Participant Tab

1.1 Add "📤 Export to Excel" QPushButton to the Participant tab toolbar (after Edit button).  
1.2 Disable it when no results are showing; enable when table has rows.  
1.3 Wire to `_on_export()`: open `QFileDialog.getSaveFileName` with `.xlsx` filter.  
1.4 Re-query the service with the same current filters but `page=1, page_size=9999` to get all rows.  
1.5 Write with openpyxl: header row + one data row per participant. Auto-size columns.  
1.6 Show success `QMessageBox` with file path, or error on failure.

## Task Group 2 — Sortable Column Headers

2.1 **Participant tab**: call `self._table.setSortingEnabled(False)` before populating rows in `refresh()`; call `self._table.setSortingEnabled(True)` after the last `setItem`.  
2.2 **Search tab**: same pattern in `_on_search()` — disable before loop, enable after.  
2.3 **Admin Audit Log**: same pattern in `_load_audit()`.  
2.4 Verify UserRole data on column 0 moves correctly with sorted rows (Qt handles this automatically for QTableWidget).

## Task Group 3 — Last Backup Indicator

3.1 Add `_get_last_backup_str() -> str` helper in `main_window.py`:
    - Scan `config.DB_PATH.parent / "backups"` for `*.db` files.
    - Return the modification time of the newest file formatted as `"Last backup: YYYY-MM-DD HH:MM"`.
    - Return `"No backup found"` if directory is empty or missing.  
3.2 Add a `QLabel` to the right side of the main window status bar showing the backup time.  
3.3 Call `_refresh_backup_label()` on startup and after every manual backup (`_on_backup()`).  
3.4 In Admin tab: add a small grey label below the Backup button showing the same info (reads from the same helper via `self.window()`).

## Task Group 4 — Cleanup

4.1 Mark TODO item done in `specs/TODO.md`.  
4.2 Syntax-check all modified files.
