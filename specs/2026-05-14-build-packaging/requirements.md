# Build & Packaging Improvements

**Date:** 2026-05-14  
**Branch:** feature/build-packaging  
**Status:** In Progress

---

## Scope

Two packaging improvements targeting both platforms:

### 1. macOS — DMG disk image
After PyInstaller produces `dist/CBMS.app`, create a distributable `.dmg` disk image using macOS's built-in `hdiutil`. The DMG contains:
- `CBMS.app`
- A symlink to `/Applications` so users can drag-and-drop to install

Output: `dist/CBMS-v<version>.dmg`

### 2. Windows — Single-file EXE by default
Change `install_and_build.bat` so that running it without arguments produces a single-file `CBMS.exe` (onefile mode) rather than a folder. A folder build is still available via `--onedir` flag. This makes Windows distribution simpler — users receive one file.

### 3. Version bump
Bump `APP_VERSION` in `app/config.py` from `"0.1.0"` to `"1.0.0"` to reflect production readiness. The DMG filename and window title will reflect this.

---

## Decisions

| Decision | Choice |
|----------|--------|
| DMG tool | `hdiutil` (built-in to macOS, no extra install) |
| DMG format | UDZO (compressed) |
| DMG filename | `CBMS-v1.0.0.dmg` in `dist/` |
| Windows default | `--onefile` (single CBMS.exe); `--onedir` flag available for folder mode |
| Version location | `app/config.py` `APP_VERSION` — single source of truth |

---

## Out of Scope
- Code signing / notarization (requires Apple Developer account)
- NSIS/Inno Setup Windows installer wizard
- Auto-update mechanism
- CI/CD pipeline
