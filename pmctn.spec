# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = [('H:\\attendance_system\\assets', 'assets'), ('H:\\attendance_system\\database', 'database'), ('H:\\attendance_system\\excel', 'excel'), ('H:\\attendance_system\\creater_database.SQL', '.')]
hiddenimports = ['PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'mysql.connector.plugins', 'mysql.connector.aio']
datas += collect_data_files('mysql')
datas += collect_data_files('mysql.connector')
hiddenimports += collect_submodules('mysql.connector')


a = Analysis(
    ['H:\\attendance_system\\main.py'],
    pathex=['H:\\attendance_system'],
    binaries=[],
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
    name='pmctn',
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
    icon=['H:\\attendance_system\\assets\\icons\\app_converted.ico'],
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pmctn',
)
