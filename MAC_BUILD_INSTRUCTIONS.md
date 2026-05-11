# CBMS macOS Build Instructions

## Quick Start (If Build Fails)

### Step 1: Clean Up Old Database
The database schema has changed. Delete the old one:

```bash
rm -f data/cbms.db
rm -f data/cbms.db-shm
rm -f data/cbms.db-wal
```

### Step 2: Run the Installer

```bash
chmod +x install_and_build.sh
./install_and_build.sh
```

This will:
1. ✅ Create a Python virtual environment
2. ✅ Install all dependencies
3. ✅ Build the macOS app bundle
4. ✅ Create a fresh database with new schema

### Step 3: Run the App

The app will be in `dist/CBMS.app`:

**Option A: From Finder**
- Navigate to `dist/CBMS.app`
- Right-click → Open
- Click "Open" when macOS warns about unsigned app

**Option B: From Terminal**
```bash
open dist/CBMS.app
```

---

## Troubleshooting

### "Can't open CBMS.app" 
This is because the app is unsigned. Do this once:
```bash
# Allow the app to run (requires once-only permission grant)
xattr -d com.apple.quarantine dist/CBMS.app
open dist/CBMS.app
```

### "ModuleNotFoundError: No module named 'sqlalchemy'"
The venv didn't activate correctly. Try:
```bash
source venv/bin/activate
python -m pip install -r requirements.txt --upgrade
python build.py
```

### "Table 'participants' already exists"
The old database schema conflicts with the new one. Delete it:
```bash
rm -f data/cbms.db*
./install_and_build.sh
```

### Port 5432 / Database Locked
If the app crashes with database errors, close any other instances:
```bash
# Check for running Python processes
ps aux | grep python

# Kill any hanging processes
pkill -f "cbms"
```

---

## Advanced: Manual Build Steps

If the script fails, do this step-by-step:

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Delete old database (schema changed)
rm -f data/cbms.db*

# 4. Build the app
python build.py

# 5. Run it
open dist/CBMS.app
```

---

## What Changed

⚠️ **Database schema has been updated** with:
- New enum fields (Gender, Population, Disease, Site, Visit Name, Sample Type, Cohort)
- User-provided PIDs (instead of auto-generated)
- 6-level storage hierarchy (Freezer → Compartment → Rack → Drawer → Box → Position)
- New columns for Excel bulk upload

**Old database is incompatible.** Always delete `data/cbms.db` before running the new version.

---

## Need More Help?

Check:
1. Python version: `python3 --version` (need 3.10+)
2. Virtual env active: `which python` should show `.../venv/bin/python`
3. Dependencies installed: `pip list | grep PyQt6`
4. Build log: Check terminal output for specific error messages

