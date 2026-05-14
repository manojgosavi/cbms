##TODO

## Now

- ~~In Participant tab, add the visit code in the display from import from excel~~ ✓ done

## Next

- ~~In Sample tab, left hierarchy should be on basis of visit code not visit name.~~ ✓ done
- ~~In Storage tab, After sample is shipped, the box color should change to grey.~~ ✓ done
- ~~In catalogue tab, add all the filters like search tab.~~ ✓ done
- ~~Look at the file /Users/manojgosavi/Downloads/FlowChart.jpeg, We need to implement this Dashboard tab below the numbers, remove the existing charts and try to implement this flow chart.~~ ✓ done
- ~~Can we implement the flowchart for the previous change we made, this doesn;t look good. Also, add filter at top right below KPI numbers for cohort type selection & then on select load the single cohort workflow. Make it more presentable.~~ ✓ done
- ~~Make change in storage hierarchy, everything looks good currently expect box is named incorrectly.~~ ✓ done Below is the detail hierarchy.
  Freezer/ Tank:
  1.NARI/COHRPICA/18-19/01 REGULAR
  2.NARI/COHRPICA/18-19/02 BACKUP
  3.NARI/COHRPICA/20-21/23 REGULAR (Cylindrical with 13 rack, 1 rack hold 1 box)
  4.NARI/COHRPICA/20-21/25 BACKUP (Cylindrical with 13 rack, 1 rack hold 1 box)

  Freezer 1 and 2 have 4 shelf : I, II, III, IV.
  Each shelf has 6 racks A, B, C, D, E, F
  Each rack has 5 drawers 01, 02, 03, 04, 05
  Each drawer will have 5 different boxes
  Each box has 10 x 10 slot positions

  Freezer 3 & 4 have no shelves. It directly has 13 racks each. 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13
  Each rack holds one box of 10 x 10 slot positions

  The Container column value is the Box name for respective Shelf, Rack and Drawer for freezer type 1 and 2. For freezer 3 and 4 there are no shelves and drawers.

- ~~Implement previous change to existing data imported from excel~~ ✓ done (run: python migrate_storage.py)
- ~~In Storage tab, in the box grid, can you adjust font so that it doesn't go outside the cell.~~ ✓ done
- ~~In Participant tab, & in general all tabs, sometime columns width are too large, can you adjust it.~~ ✓ done
- ~~In Sample tab, search by typing PID, checkboxes for multiple selection, sorted option. The filter should be similar to what we have in excel worksheet column.~~ ✓ done
- ~~In Search tab, there are 3 changes, firstly can you add unblock selected button at top right and unblock functionality with reason.This should be enabled for all users type.Secondly add visit code filter in left pane.Lastly, add population filter in left pane & change the age filter heading to age, currently is population. Also check search by cohort , it is not returning results.~~ ✓ done
- ~~Fix: double-clicking a record in Search tab should navigate to the Storage tab and highlight the aliquot's box position in the box grid.~~ ✓ done
- ~~Add pagination whereever necessary.~~ ✓ done
- ~~Any other improvement that is currently missing and should be implemented.~~ ✓ done (export from participant tab, sortable columns, last backup indicator)
- ~~Any improvement on building & installing the app.~~ ✓ done (macOS DMG via hdiutil, Windows onefile EXE default, version bumped to 1.0.0)
