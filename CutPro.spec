# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['PIL._tkinter_finder', 'tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'customtkinter', 'PIL', 'PIL.Image', 'cv2', 'inspect', 'pkg_resources', 'importlib_metadata', 'threading', 'subprocess', 'pathlib', 'json', 'requests', 'uuid', 'datetime', 'hashlib', 'urllib3', 'urllib3.util', 'urllib3.util.retry', 'requests.adapters', 'ssl', 'certifi', 'charset_normalizer', 'idna', 'zipfile', 'shutil', 'platform', 'packaging', 'packaging.version', 'packaging.specifiers', 'packaging.requirements', 'updater', 'tempfile']
hiddenimports += collect_submodules('urllib3')
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('PIL')


a = Analysis(
    ['auto.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.'), ('icon.ico', '.'), ('version.txt', '.'), ('updater.py', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'test', 'pdb', 'doctest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CutPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
