#!/bin/bash
# =============================================================================
# CBMS — Mac installer and build script
#
# What this does:
#   1. Checks Python 3.10+ is available
#   2. Creates a virtual environment (venv/) if not already present
#   3. Installs all dependencies from requirements.txt
#   4. Installs PyInstaller
#   5. Builds the CBMS.app bundle via build.py
#
# Usage:
#   chmod +x install_and_build.sh   # only needed once
#   ./install_and_build.sh          # normal build
#   ./install_and_build.sh --onefile  # single-file bundle
#
# Output:
#   dist/CBMS/        (folder mode — default, faster startup)
#   dist/CBMS.app     (onefile mode)
# =============================================================================

set -e  # exit immediately on any error

PYTHON=""
ONEFILE_FLAG=""

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
    if [ "$arg" = "--onefile" ]; then
        ONEFILE_FLAG="--onefile"
    fi
done

# ── Step 1: Find Python 3.10+ ─────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   CBMS — Mac Installer & Build               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "▶ Checking Python version..."

for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" -c "import sys; print(sys.version_info[:2])")
        MAJOR=$("$cmd" -c "import sys; print(sys.version_info[0])")
        MINOR=$("$cmd" -c "import sys; print(sys.version_info[1])")
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON="$cmd"
            echo "  ✓ Found $cmd ($(${cmd} --version))"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "  ✗ Python 3.10 or higher is required but not found."
    echo "    Install it from: https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# ── Step 2: Create virtual environment ────────────────────────────────────────
echo ""
echo "▶ Setting up virtual environment..."

if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "  ✓ Created venv/"
else
    echo "  ✓ venv/ already exists — skipping creation"
fi

# Activate venv
source venv/bin/activate
echo "  ✓ Activated venv"

# ── Step 3: Upgrade pip quietly ───────────────────────────────────────────────
echo ""
echo "▶ Upgrading pip..."
pip install --upgrade pip --quiet
echo "  ✓ pip up to date"

# ── Step 4: Install dependencies ──────────────────────────────────────────────
echo ""
echo "▶ Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet
echo "  ✓ Dependencies installed"

# ── Step 5: Install PyInstaller ───────────────────────────────────────────────
echo ""
echo "▶ Installing PyInstaller..."
pip install pyinstaller --quiet
echo "  ✓ PyInstaller installed"

# ── Step 6: Build ─────────────────────────────────────────────────────────────
echo ""
echo "▶ Building CBMS app..."
echo ""

python build.py $ONEFILE_FLAG

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Build complete!                            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
if [ -n "$ONEFILE_FLAG" ]; then
    echo "  App bundle: dist/CBMS"
else
    echo "  App folder: dist/CBMS/"
fi
echo ""
echo "  To run directly without building:"
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""