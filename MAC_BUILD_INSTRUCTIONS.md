# CBMS macOS Build Instructions

## Quick Start

### Step 1: Run the Installer & Build

```bash
chmod +x install_and_build.sh
./install_and_build.sh
```

This will:
1. ✅ Create a Python virtual environment
2. ✅ Install all dependencies
3. ✅ Build `dist/CBMS.app`
4. ✅ Create `dist/CBMS-v1.0.0.dmg` (drag-and-drop installer)

### Step 2: Distribute via DMG

Open the DMG and drag **CBMS** to the **Applications** folder:

```bash
open dist/CBMS-v1.0.0.dmg
```

### Step 3: First Launch (Gatekeeper)

Because the app is unsigned, macOS will block it the first time:

**Option A — Right-click method:**
- In Finder, right-click `CBMS.app` → **Open** → click **Open**

**Option B — Terminal (once only):**
```bash
xattr -d com.apple.quarantine /Applications/CBMS.app
open /Applications/CBMS.app
```

---

## Running Without Building

For development or quick testing, skip the build entirely:

```bash
source venv/bin/activate
python main.py
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"
The venv didn't activate. Run:
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
python build.py
```

### "Can't create DMG" / hdiutil error
The DMG step requires `dist/CBMS.app` to exist. Make sure the PyInstaller step completed successfully first (check for errors in the build output).

### Database issues on first run
If the app crashes with a database error, delete the old database and let it recreate:
```bash
rm -f data/cbms.db data/cbms.db-shm data/cbms.db-wal
open dist/CBMS.app
```

---

## Manual Build Steps

If the script fails, run each step individually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python build.py           # builds CBMS.app + DMG
```

---

## Need More Help?

1. Python version: `python3 --version` (need 3.10+)
2. Virtual env active: `which python` should show `.../venv/bin/python`
3. Dependencies installed: `pip list | grep PyQt6`
4. Build log: check terminal output for the specific error line
