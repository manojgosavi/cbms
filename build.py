"""
CBMS build script — produces a standalone executable using PyInstaller.

Usage:
  python build.py            # auto-detects platform
  python build.py --onefile  # single-file bundle (slower startup, easier to share)

Output:
  dist/CBMS/          (folder mode — fast startup, recommended)
  dist/CBMS.exe       (Windows single-file mode)
  dist/CBMS.app       (macOS app bundle)

Key concept — PyInstaller:
  PyInstaller analyses your imports and bundles Python + all dependencies
  into a folder or single executable. The user needs no Python installed.

  --hidden-import: modules PyInstaller misses because they're imported
    dynamically (e.g. via __import__() or importlib).
  --add-data: non-Python files (icons, themes) that must be included.
  --windowed: suppresses the terminal window on Windows/macOS (GUI apps).
  --onefile: single .exe/.app (convenient but slower startup due to unpacking).
"""

import os
import platform
import subprocess
import sys


def build(onefile: bool = False):
    system  = platform.system()
    is_mac  = system == "Darwin"
    is_win  = system == "Windows"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CBMS",
        "--clean",
        "--noconfirm",
        # suppress terminal window on GUI platforms
        "--windowed" if (is_mac or is_win) else "--console",
        # hidden imports PyInstaller often misses
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "bcrypt",
        "--hidden-import", "openpyxl",
        "--hidden-import", "matplotlib.backends.backend_qtagg",
        "--hidden-import", "matplotlib.backends.backend_agg",
        "--hidden-import", "matplotlib",
        "--hidden-import", "PyQt6.sip",
        # matplotlib bundles data files (fonts, styles, backends) that
        # PyInstaller won't find automatically — must be added explicitly.
        "--add-data", f"{__import__('matplotlib').get_data_path()}{os.pathsep}matplotlib/mpl-data",
        "--collect-data", "matplotlib",
        # numpy 2.x restructured internal modules — collect-all is required
        # otherwise numpy._core._exceptions and similar are missing in the bundle
        "--collect-all", "numpy",
        # include non-Python data files
        "--add-data", f"resources{os.pathsep}resources",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    # macOS: set icon (.icns), Windows: set icon (.ico)
    icon_path = None
    if is_mac and os.path.exists("resources/icons/cbms.icns"):
        icon_path = "resources/icons/cbms.icns"
    elif is_win and os.path.exists("resources/icons/cbms.ico"):
        icon_path = "resources/icons/cbms.ico"

    if icon_path:
        args += ["--icon", icon_path]

    args.append("main.py")

    print(f"[CBMS Build] Platform: {system}")
    print(f"[CBMS Build] Mode: {'onefile' if onefile else 'onedir'}")
    print(f"[CBMS Build] Running: {' '.join(args)}\n")

    result = subprocess.run(args)

    if result.returncode == 0:
        print("\n[CBMS Build] Build successful!")
        if onefile:
            ext = ".exe" if is_win else ""
            print(f"  Executable: dist/CBMS{ext}")
        else:
            print(f"  Output folder: dist/CBMS/")
    else:
        print("\n[CBMS Build] Build failed — see output above.")
        sys.exit(1)


if __name__ == "__main__":
    onefile = "--onefile" in sys.argv
    build(onefile=onefile)