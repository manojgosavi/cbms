# Validation — Build & Packaging

## Manual Test Cases

### V1 — Version number updated
1. Run the app (`python main.py`).
2. Window title shows "Central Biorepository Management Software  v1.0.0".
3. Help → About shows version 1.0.0.

### V2 — macOS DMG created
1. On macOS, run `./install_and_build.sh`.
2. Build completes without error.
3. `dist/CBMS-v1.0.0.dmg` exists.
4. Double-clicking the DMG mounts it; shows CBMS.app and an Applications shortcut.
5. Dragging CBMS.app to Applications installs it successfully.
6. Launched app from /Applications shows the correct version.

### V3 — Windows EXE (single file)
1. On Windows, run `install_and_build.bat` (no flags).
2. Build completes; `dist\CBMS.exe` is produced (not a folder).
3. Double-clicking `CBMS.exe` launches the app.
4. Running `install_and_build.bat --onedir` produces `dist\CBMS\` folder instead.

### V4 — No regression on app functionality
1. Built app opens, shows login screen.
2. Import, Search, Storage, Dashboard all function correctly in the packaged build.

## Pass Criteria
V1 passes on any platform.  
V2 passes on macOS.  
V3 passes on Windows.  
V4 passes on the primary test platform.
