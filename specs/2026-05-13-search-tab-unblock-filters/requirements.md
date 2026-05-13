# Search Tab — Unblock, Visit Code Filter, Population Filter, Cohort Bug Fix

**Date:** 2026-05-13  
**Branch:** feature/search-tab-unblock-filters-fix  
**Status:** In Progress

---

## Scope

Four changes to the Search tab and its backing service:

1. **Unblock selected** — new button in the results toolbar; opens a dedicated Unblock dialog capturing a release reason; enabled for all user roles.
2. **Visit Code filter** — new free-text partial-match filter in the left pane.
3. **Population filter** — new free-text partial-match filter in the left pane; rename the existing mislabelled "Population" section header above Age to "Age".
4. **Cohort bug fix** — `search_service.py` line 164 checks `filters.cohort` but mistakenly queries `filters.cohort_name` (which is always `None`), causing cohort searches to return no results.

---

## Decisions

| Decision | Choice |
|----------|--------|
| Unblock permission | Remove `app_session.require("sample.edit")` from `release_block()` and `release_multiple()` only — any logged-in user can unblock |
| Unblock UX | Dedicated `UnblockDialog` (new file) with reason QLineEdit + list of selected aliquot IDs |
| Filter style | Both Visit Code and Population as free-text partial match (consistent with existing filters) |

---

## Context

Current state of `SearchFilters` dataclass:
- Has `cohort_name` field; search_tab sets `f.cohort` (mismatch → bug)
- Has `visit_code` field but no condition in service and no widget in UI
- Has `population` field but no widget in UI
- Age SpinBox is under a section label wrongly titled "Population"

After this change:
- `SearchFilters.cohort_name` renamed to `cohort` (or service fixed to use correct attribute)
- Visit Code widget added to left pane; service condition added
- Population widget added to left pane; section label "Population" → "Age" above the Age spinner
- `release_block` / `release_multiple` no longer gated by `sample.edit`
- "Unblock selected" button enabled for all users; disabled when selection has no blocked aliquots

---

## Out of Scope

- Changing the Block dialog or Block permission
- Adding unblock to the Storage tab
- Scheduling automatic unblock on overdue blocks
