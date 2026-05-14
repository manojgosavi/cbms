"""
CBMS build script — produces a standalone executable using PyInstaller.

Usage:
  python build.py            # auto-detects platform; onedir on macOS/Linux, onefile on Windows
  python build.py --onefile  # single-file bundle (slower startup, easier to share)
  python build.py --onedir   # folder output (fast startup)

Output:
  macOS:   dist/CBMS.app  +  dist/CBMS-v<version>.dmg
  Windows: dist/CBMS.exe  (onefile default)
  Linux:   dist/CBMS/     (onedir default)
"""

import os
import platform
import shutil
import subprocess
import sys


def _get_version() -> str:
    try:
        from app.config import APP_VERSION
        return APP_VERSION
    except Exception:
        return "1.0.0"


def create_dmg(version: str) -> None:
    """Create a distributable DMG from dist/CBMS.app using hdiutil."""
    app_path = "dist/CBMS.app"
    if not os.path.exists(app_path):
        print("[CBMS Build] Skipping DMG — dist/CBMS.app not found.")
        return

    staging = "dist/dmg_staging"
    dmg_path = f"dist/CBMS-v{version}.dmg"

    print(f"\n[CBMS Build] Creating DMG: {dmg_path}")

    # Clean up any leftover staging dir
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    # Copy app into staging
    shutil.copytree(app_path, os.path.join(staging, "CBMS.app"))

    # Symlink to /Applications so users can drag-and-drop
    os.symlink("/Applications", os.path.join(staging, "Applications"))

    # Remove old DMG if it exists (hdiutil won't overwrite)
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    result = subprocess.run([
        "hdiutil", "create",
        "-srcfolder", staging,
        "-volname", "CBMS",
        "-format", "UDZO",
        "-imagekey", "zlib-level=9",
        "-o", dmg_path,
    ])

    # Clean up staging dir
    shutil.rmtree(staging)

    if result.returncode == 0:
        print(f"[CBMS Build] DMG created: {dmg_path}")
    else:
        print("[CBMS Build] DMG creation failed — hdiutil error above.")


def build(onefile: bool = False, onedir: bool = False):
    system = platform.system()
    is_mac = system == "Darwin"
    is_win = system == "Windows"
    version = _get_version()

    # Default mode: onefile on Windows, onedir on macOS/Linux
    if not onefile and not onedir:
        onefile = is_win

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CBMS",
        "--clean",
        "--noconfirm",
        "--windowed" if (is_mac or is_win) else "--console",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "bcrypt",
        "--hidden-import", "openpyxl",
        "--hidden-import", "matplotlib.backends.backend_qtagg",
        "--hidden-import", "matplotlib.backends.backend_agg",
        "--hidden-import", "matplotlib",
        "--hidden-import", "PyQt6.sip",
        "--add-data", f"{__import__('matplotlib').get_data_path()}{os.pathsep}matplotlib/mpl-data",
        "--collect-data", "matplotlib",
        "--collect-all", "numpy",
        "--add-data", f"resources{os.pathsep}resources",
    ]

    args.append("--onefile" if onefile else "--onedir")

    icon_path = None
    if is_mac and os.path.exists("resources/icons/cbms.icns"):
        icon_path = "resources/icons/cbms.icns"
    elif is_win and os.path.exists("resources/icons/cbms.ico"):
        icon_path = "resources/icons/cbms.ico"
    if icon_path:
        args += ["--icon", icon_path]

    args.append("main.py")

    print(f"[CBMS Build] Platform : {system}")
    print(f"[CBMS Build] Version  : {version}")
    print(f"[CBMS Build] Mode     : {'onefile' if onefile else 'onedir'}")
    print(f"[CBMS Build] Running  : {' '.join(args)}\n")

    result = subprocess.run(args)

    if result.returncode != 0:
        print("\n[CBMS Build] Build failed — see output above.")
        sys.exit(1)

    print("\n[CBMS Build] Build successful!")
    if onefile:
        ext = ".exe" if is_win else ""
        print(f"  Executable : dist/CBMS{ext}")
    else:
        if is_mac:
            print(f"  App bundle : dist/CBMS.app")
            create_dmg(version)
            print(f"  DMG        : dist/CBMS-v{version}.dmg")
        else:
            print(f"  Folder     : dist/CBMS/")


if __name__ == "__main__":
    onefile = "--onefile" in sys.argv
    onedir  = "--onedir"  in sys.argv
    build(onefile=onefile, onedir=onedir)
