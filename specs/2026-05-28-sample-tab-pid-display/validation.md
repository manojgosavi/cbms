# Validation: Sample Tab — PID-Based Display & Visit Code Column

---

## Manual Test Cases

### TC-1: Right Pane — PID in ID Column
**Setup:** Select a study, check one participant (e.g., PID = `12345-COHRPICA`).
**Expected:** Each sample row in the right tree shows `12345-COHRPICA` in column 0, not the internal serial like `COH-26-1`.

### TC-2: Right Pane — Visit Code Column Populated
**Setup:** Same as TC-1, participant with samples that have a `visit_code` (e.g., `M0`, `SCR(NA)`).
**Expected:** Column "Visit Code" shows the correct visit code for each sample row. Rows without a visit code show blank.

### TC-3: Right Pane — Visit Code Column Empty When Missing
**Setup:** Participant with a sample where `visit_code` is NULL.
**Expected:** Visit Code cell is blank (no crash, no `None` text shown).

### TC-4: Left Pane Visit Tree — Children Show PID
**Setup:** Select participant, expand a visit code node in the bottom-left visit tree.
**Expected:** Child items show the participant PID (e.g., `12345-COHRPICA`) instead of `COH-26-1`.

### TC-5: Disambiguation — Multiple Samples per PID per Visit
**Setup:** A participant with two samples under the same visit (e.g., Serum + PBMC at M0).
**Expected:** Visit tree children are `12345-COHRPICA (Serum)` and `12345-COHRPICA (PBMC)` — not duplicate identical labels.

### TC-6: Multi-Participant Selection
**Setup:** Check two participants in the left list.
**Expected:** Right pane shows all their samples, each with correct PID in column 0.

### TC-7: Edit Sample Still Works
**Setup:** Select a sample row, click "✎ Edit".
**Expected:** SampleDialog opens correctly, pre-filled with the sample's data. Saving works and tree refreshes.

### TC-8: Add Aliquots Still Works
**Setup:** Select a sample row, click "＋ Add Aliquots".
**Expected:** AddAliquotsDialog opens; new aliquots appear as child rows after save.

### TC-9: Visit Filter Still Works
**Setup:** Click a specific visit code in the bottom-left tree (e.g., "M0").
**Expected:** Right pane filters to only samples for that visit code. PID column still correct.

### TC-10: Aliquot Child Rows Unaffected
**Setup:** Expand a sample row in the right tree.
**Expected:** Aliquot child rows still show their aliquot_id (e.g., `↳ COH-26-1-A1`) — only the parent sample row shows PID.

---

## Regression Checks
- [ ] Sorting/filtering in visit tree still works after label change.
- [ ] Column resize modes are correct for the 7-column layout.
- [ ] `_sample_count_lbl` still shows correct count.
- [ ] No `AttributeError` when `s.participant` is None (should not happen given FK, but guard if needed).
