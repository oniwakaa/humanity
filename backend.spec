# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = []
# Include metadata for packages that need it (often required for chroma/pydantic/etc config)
datas += copy_metadata('chromadb')
datas += copy_metadata('tqdm')

datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('posthog')

# Include models directory or other assets if needed
# datas += [('models', 'models')] 

block_cipher = None

a = Analysis(
    ['api/server.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn', 
        'fastapi', 
        'chromadb', 
        'chromadb.api.segment',
        'chromadb.api.rust',
        'chromadb.db.impl.sqlite',
        'chromadb.migrations',
        'chromadb.telemetry.product.posthog',
        'pydantic', 
        'rich',
        'rich.console', 
        'rich.panel', 
        'rich.prompt',
        'connectors',
        'connectors.ollama',
        'settings',
        'settings.manager',
        'orchestrator'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='humanity-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
