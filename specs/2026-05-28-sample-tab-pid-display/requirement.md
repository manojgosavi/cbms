# Requirement: Sample Tab — PID-Based Display & Visit Code Column

## Source
TODO.md — last open item:
> In Samples tab, ID shown should be the PID selected from left pane. Can you remove the sample ID auto generated & replace it with PID. Also add the visit code column in right pane. Bottom left pane showing data visit code wise should also show PIDs & not auto generated sample IDs.

---

## Problem Statement
The Samples tab currently displays an internally auto-generated Sample ID (format: `COH-26-1`, `COH-26-2`, …) in both the right-pane sample tree and the bottom-left visit-code hierarchy. This ID is not meaningful to lab staff — they know participants by their PID, not by internal serial numbers.

---

## Functional Requirements

### FR-1: Right Pane — "ID" Column Shows PID
- The first column ("ID") of the right-pane sample tree must show the participant's PID (e.g., `12345-COHRPICA`) for every sample row.
- Child aliquot rows in the tree may keep their aliquot_id (e.g., `COH-26-1-A1`) or derive from PID — **TBD** (see open questions).

### FR-2: Right Pane — Add "Visit Code" Column
- Insert a "Visit Code" column in the sample tree header.
- Populate it from `Sample.visit_code` for each sample row.
- Column position: after "ID" (column index 1), shifting Type, Collection Date, etc.

### FR-3: Left Pane — Visit Code Tree Shows PIDs
- The bottom-left visit-code tree currently lists children as `sample_id` strings (e.g., `  COH-26-1`).
- Replace these child labels with the participant PID (e.g., `  12345-COHRPICA`).
- When multiple samples exist for the same PID under one visit, disambiguate (e.g., append sample type: `12345-COHRPICA (Serum)`).

---

## Out of Scope
- Changing the actual stored `Sample.sample_id` in the database (display only, unless confirmed otherwise).
- Changing aliquot_id format stored in DB.
- Any changes to the Search tab, Storage tab, or shipment flows.

---

## Confirmed Decisions
1. **Display only** — stored `sample_id` stays auto-generated in DB; no migration needed.
2. **ID column shows PID only** — multiple samples for the same PID are distinguished by the Type / Visit Code columns.
3. **Aliquot child rows** keep their current `aliquot_id` format (e.g., `COH-26-1-A1`).
4. **Visit Code column** is inserted after ID (column order: ID | Visit Code | Type | Collection Date | Vol | Status | Discrepancy).
