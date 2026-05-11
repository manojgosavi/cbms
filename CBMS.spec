# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('/Users/manojgosavi/Downloads/cbms_with_excel_import_clean/venv/lib/python3.12/site-packages/matplotlib/mpl-data', 'matplotlib/mpl-data'), ('resources', 'resources')]
binaries = []
hiddenimports = ['sqlalchemy.dialects.sqlite', 'bcrypt', 'openpyxl', 'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_agg', 'matplotlib', 'PyQt6.sip']
datas += collect_data_files('matplotlib')
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CBMS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/icons/cbms.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CBMS',
)
app = BUNDLE(
    coll,
    name='CBMS.app',
    icon='resources/icons/cbms.icns',
    bundle_identifier=None,
)
