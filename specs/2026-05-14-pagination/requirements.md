# Pagination — Participant, Search, Audit Log, Reports

**Date:** 2026-05-14  
**Branch:** feature/pagination  
**Status:** In Progress

---

## Scope

Add Prev / Next pagination (100 rows per page) to four tabs:

| Tab | Current cap | Change |
|-----|------------|--------|
| Participant | 200 hardcoded | 100/page with Prev/Next |
| Search | 200 hardcoded | 100/page with Prev/Next |
| Audit Log (Admin) | 500 hardcoded | 100/page with Prev/Next |
| Reports | No cap | 100/page with Prev/Next |

---

## Decisions

| Decision | Choice |
|----------|--------|
| Page size | 100 rows |
| UI | "◀ Prev" button · "Page X of Y (N total)" label · "Next ▶" button |
| Shared widget | `PaginationBar(QWidget)` in `app/ui/widgets/pagination_bar.py` — reused in all 4 tabs |
| Filter/search reset | Any change to search filters resets to page 1 before reloading |
| Service layer | `ParticipantService.search()` and `SearchService.search()` already accept `page` / `page_size`; audit and reports queries need offset/limit added |

---

## Context

With 1380 rows imported from the test file, the Participant tab would silently truncate at 200 and users would not know records were missing. All four tabs need consistent, visible pagination.

---

## Out of Scope

- Jump-to-page input
- Configurable page size setting
- Pagination in the Sample tab PID list (500 cap is acceptable for a single study)
