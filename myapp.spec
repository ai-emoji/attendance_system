# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('E:\\attendance_system1\\assets', 'assets'), ('E:\\attendance_system1\\database', 'database'), ('E:\\attendance_system1\\creater_database.SQL', '.')]
binaries = []
hiddenimports = ['PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'mysql.connector.plugins', 'mysql.connector.aio']
datas += collect_data_files('mysql')
datas += collect_data_files('mysql.connector')
hiddenimports += collect_submodules('mysql.connector')
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['E:\\attendance_system1\\main.py'],
    pathex=['E:\\attendance_system1'],
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
    name='myapp',
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
    icon=['E:\\attendance_system1\\assets\\icons\\app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='myapp',
)
