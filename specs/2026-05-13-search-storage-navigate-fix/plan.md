# Plan — Search → Storage Navigation Fix

## Task Group 1 — BoxGridWidget: add select_cell()

1.1 Add `select_cell(row: int, col: int) -> None` to `BoxGridWidget`.  
1.2 Sets `self._selected_cell = (row, col)` and calls `self.update()`.  
1.3 Also scrolls the widget if needed (widget is fixed-size so no scroll required).

## Task Group 2 — StorageTab: add navigate_to_aliquot()

2.1 Add `navigate_to_aliquot(aliquot_db_id: int) -> None` to `StorageTab`.  
2.2 Inside a `get_session()` block, query:
    - `AliquotLocation` where `aliquot_id == aliquot_db_id` → get `position_id`
    - `BoxPosition` where `id == position_id` → get `box_id`, `row`, `col`
2.3 If no location found: show `QMessageBox.information` "No storage location recorded for this aliquot." and return.  
2.4 Walk the `QTreeWidget` recursively to find the item whose `UserRole` data is `("box", box_id)`.  
2.5 Call `self._tree.setCurrentItem(box_item)` and `self._tree.scrollToItem(box_item)`.  
2.6 Call `self._load_box_grid(box_id)` to render the grid.  
2.7 Call `self._box_grid.select_cell(row, col)` to highlight the cell.

## Task Group 3 — MainWindow: wire show_aliquot_location()

3.1 Update `show_aliquot_location(aliquot_db_id)` to call:
    ```python
    self.tabs.setCurrentWidget(self.storage_tab)
    self.storage_tab.navigate_to_aliquot(aliquot_db_id)
    ```

## Task Group 4 — Cleanup

4.1 Mark TODO item done in `specs/TODO.md`.  
4.2 Syntax-check all modified files.
