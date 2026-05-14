# Plan — Build & Packaging

## Task Group 1 — Version bump

1.1 Change `APP_VERSION = "0.1.0"` → `"1.0.0"` in `app/config.py`.

## Task Group 2 — macOS DMG creation

2.1 Add `create_dmg(version: str)` function to `build.py`:
    - Create `dist/dmg_staging/` directory.
    - Copy `dist/CBMS.app` into staging dir.
    - Create a symlink `dist/dmg_staging/Applications → /Applications`.
    - Run `hdiutil create -srcfolder dist/dmg_staging -volname "CBMS" -format UDZO -imagekey zlib-level=9 -o dist/CBMS-v{version}.dmg`.
    - Remove `dist/dmg_staging/` after DMG is created.  
2.2 Call `create_dmg(version)` from `build()` on macOS after PyInstaller succeeds (only in `--onedir` mode, since `CBMS.app` is only produced in that mode on macOS).  
2.3 Print the DMG path in the build success message.

2.4 Add a DMG creation step to `install_and_build.sh`:
    - After `python build.py`, call the DMG step (already handled inside `build.py` on macOS).
    - Update the "Build complete" message to show the `.dmg` path.

## Task Group 3 — Windows onefile default

3.1 In `install_and_build.bat`:
    - Change the default from folder mode to `--onefile`.
    - Rename the override flag from `--onefile` → `--onedir` (for users who want the folder).
    - Update help comments and final output message accordingly.  
3.2 In `build.py`: no changes needed — `--onefile` flag is already supported.  
3.3 Update `install_and_build.bat` comments to reflect new defaults.

## Task Group 4 — Update README and MAC_BUILD_INSTRUCTIONS

4.1 Update `MAC_BUILD_INSTRUCTIONS.md`:
    - Add "Step 4: Distribute via DMG" section explaining the output path.
    - Note the Gatekeeper workaround (`xattr -d com.apple.quarantine`) still applies.  
4.2 Update `README.md` build section to mention the DMG output and Windows EXE.

## Task Group 5 — Cleanup

5.1 Mark TODO item done in `specs/TODO.md`.  
5.2 Syntax-check `build.py` and `app/config.py`.
