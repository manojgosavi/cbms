# Plan — Pagination

## Task Group 1 — PaginationBar shared widget (new file)

1.1 Create `app/ui/widgets/pagination_bar.py`.  
1.2 `PaginationBar(QWidget)` with signal `page_changed = pyqtSignal(int)`.  
1.3 Layout: "◀ Prev" QPushButton · "Page X of Y (N total)" QLabel · "Next ▶" QPushButton.  
1.4 `set_page(current: int, total_pages: int, total_items: int)` — updates label, disables Prev on page 1, disables Next on last page.  
1.5 Prev/Next clicks emit `page_changed(new_page)`.

## Task Group 2 — Participant tab

2.1 Add `self._page = 1` state variable.  
2.2 Add `PaginationBar` below the table in `_build_ui()`.  
2.3 Connect `_pagination.page_changed` → set `self._page` → call `refresh()`.  
2.4 In `refresh()`: pass `page=self._page, page_size=100`; call `_pagination.set_page(page, ceil(total/100), total)`.  
2.5 On any filter change (`_study_filter`, `_pid_search`): reset `self._page = 1` before refresh.

## Task Group 3 — Search tab

3.1 Add `self._page = 1` state variable.  
3.2 Add `PaginationBar` below the table.  
3.3 Connect `page_changed` → set page → `_on_search()`.  
3.4 In `_on_search()`: if called from button/filter (not page turn), reset `self._page = 1`.  
3.5 Pass `page=self._page, page_size=100` to `SearchService.search()`; update pagination bar.  
3.6 Keep selected-row actions (Block, Unblock, Ship, Export current page) working correctly.

## Task Group 4 — Admin tab — Audit Log

4.1 Read admin_tab.py to find the audit log query; add `self._audit_page = 1`.  
4.2 Add `PaginationBar` below the audit table.  
4.3 Wrap audit query with `.offset((page-1)*100).limit(100)` and a separate `.count()`.  
4.4 Connect page changes to reload audit table.  
4.5 Any filter change on audit log resets to page 1.

## Task Group 5 — Reports tab

5.1 Read reports_tab.py to find the data query; add `self._report_page = 1`.  
5.2 Add `PaginationBar` below the reports table.  
5.3 Slice the in-memory result list by page: `rows[start:end]`.  
5.4 On filter change or new report load: reset to page 1.

## Task Group 6 — Cleanup

6.1 Mark TODO item done.  
6.2 Syntax-check all modified files.
