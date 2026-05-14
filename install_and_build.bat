@echo off
REM =============================================================================
REM CBMS — Windows installer and build script
REM
REM What this does:
REM   1. Checks Python 3.10+ is available
REM   2. Creates a virtual environment (venv\) if not already present
REM   3. Installs all dependencies from requirements.txt
REM   4. Installs PyInstaller
REM   5. Builds CBMS.exe (single-file, default) via build.py
REM
REM Usage:
REM   install_and_build.bat           (default — single CBMS.exe)
REM   install_and_build.bat --onedir  (folder mode — faster startup)
REM
REM Output:
REM   dist\CBMS.exe     (default — single file, easy to distribute)
REM   dist\CBMS\        (--onedir mode — faster startup)
REM =============================================================================

setlocal EnableDelayedExpansion

REM Default: onefile (single CBMS.exe)
set BUILD_FLAG=--onefile

REM ── Parse args ────────────────────────────────────────────────────────────────
for %%A in (%*) do (
    if "%%A"=="--onedir" set BUILD_FLAG=--onedir
)

echo.
echo +----------------------------------------------+
echo ^|   CBMS -- Windows Installer ^& Build          ^|
echo +----------------------------------------------+
echo.

REM ── Step 1: Find Python 3.10+ ─────────────────────────────────────────────────
echo ^> Checking Python version...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   X Python not found.
    echo     Install it from: https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check version is at least 3.10
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%A in ("%PYVER%") do (
    set PYMAJOR=%%A
    set PYMINOR=%%B
)

if %PYMAJOR% LSS 3 (
    echo   X Python 3.10+ required. Found %PYVER%.
    pause
    exit /b 1
)
if %PYMAJOR% EQU 3 if %PYMINOR% LSS 10 (
    echo   X Python 3.10+ required. Found %PYVER%.
    pause
    exit /b 1
)

echo   OK Found Python %PYVER%

REM ── Step 2: Create virtual environment ────────────────────────────────────────
echo.
echo ^> Setting up virtual environment...

if not exist "venv\" (
    python -m venv venv
    echo   OK Created venv\
) else (
    echo   OK venv\ already exists -- skipping creation
)

REM Activate venv
call venv\Scripts\activate.bat
echo   OK Activated venv

REM ── Step 3: Upgrade pip ───────────────────────────────────────────────────────
echo.
echo ^> Upgrading pip...
pip install --upgrade pip --quiet
echo   OK pip up to date

REM ── Step 4: Install dependencies ──────────────────────────────────────────────
echo.
echo ^> Installing dependencies from requirements.txt...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   X Failed to install dependencies.
    pause
    exit /b 1
)
echo   OK Dependencies installed

REM ── Step 5: Install PyInstaller ───────────────────────────────────────────────
echo.
echo ^> Installing PyInstaller...
pip install pyinstaller --quiet
echo   OK PyInstaller installed

REM ── Step 6: Build ─────────────────────────────────────────────────────────────
echo.
echo ^> Building CBMS app...
echo.

python build.py %BUILD_FLAG%
if errorlevel 1 (
    echo.
    echo   X Build failed. See output above.
    pause
    exit /b 1
)

REM ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo +----------------------------------------------+
echo ^|   Build complete!                            ^|
echo +----------------------------------------------+
echo.
if "%BUILD_FLAG%"=="--onedir" (
    echo   App folder: dist\CBMS\
) else (
    echo   Executable: dist\CBMS.exe
)
echo.
echo   To run directly without building:
echo     venv\Scripts\activate
echo     python main.py
echo.
pause
