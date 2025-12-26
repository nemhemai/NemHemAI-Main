# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None
project_dir = os.path.abspath('.')

# Collect all frontend build files from dist directory
frontend_files = []
dist_dir = os.path.join(project_dir, 'dist')
if os.path.exists(dist_dir):
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, project_dir)
            frontend_files.append((file_path, rel_path))

a = Analysis(
    ['desktop_launcher.py'],
    pathex=[project_dir],
    binaries=[],
    datas=frontend_files + [
        (os.path.join('backend', 'requirements.txt'), 'backend'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'passlib.handlers.bcrypt',
        'sqlalchemy.sql.default_comparator',
        'sklearn.utils._typedefs',
        'sklearn.neighbors._partition_nodes',
        'sklearn.tree._utils',
        'scipy.special._ufuncs_cxx',
        'scipy._lib.messagestream',
        'PIL._tkinter_finder',
        'pytesseract',
        'docx',
        'PyPDF2',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.skiplist',
        'matplotlib.backends.backend_agg',
        'seaborn',
        'plotly',
        'chardet',
        'webview',
        'webview.platforms',
        'webview.platforms.cocoa',  # Mac specific
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'tkinter',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
        'test',
        '_pytest',
        'py',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NemhemAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False for Mac app to avoid terminal window
    disable_windowed_traceback=False,
    argv_emulation=True,  # Recommended for Mac
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='public/icon.icns' if os.path.exists('public/icon.icns') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NemhemAI',
)

app = BUNDLE(
    coll,
    name='NemhemAI.app',
    icon='public/icon.icns' if os.path.exists('public/icon.icns') else None,
    bundle_identifier='com.nemhemai.app',
)
