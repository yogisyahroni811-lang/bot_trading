# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for Sentinel-X
Builds single-file executable with all dependencies embedded.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from packages
datas = []

# CustomTkinter assets
datas += collect_data_files('customtkinter')

# LangChain data files
datas += collect_data_files('langchain')
datas += collect_data_files('langchain_openai')
datas += collect_data_files('langchain_google_genai')

# ChromaDB data files
datas += collect_data_files('chromadb')

# Add migrations directory
datas += [('migrations', 'migrations')]

# Add knowledge directory (empty template)
datas += [('knowledge', 'knowledge')]

# Collect hidden imports (packages not auto-detected)
hiddenimports = []

# Core ML/AI packages
hiddenimports += collect_submodules('tiktoken')
hiddenimports += collect_submodules('openai')
hiddenimports += collect_submodules('anthropic')
hiddenimports += collect_submodules('google.generativeai')

# FastAPI & Uvicorn
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('starlette')

# ChromaDB dependencies
hiddenimports += collect_submodules('chromadb')
hiddenimports += collect_submodules('hnswlib')
hiddenimports += collect_submodules('pypdf')

# Cryptography
hiddenimports += ['cryptography.hazmat.backends.openssl']
hiddenimports += ['cryptography.hazmat.primitives.ciphers.aead']

# Additional runtime dependencies
hiddenimports += [
    'sqlite3',
    'json',
    'threading',
    'queue',
    'multiprocessing',
]

a = Analysis(
    ['gui.py'],  # Main entry point
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib.tests',
        'numpy.testing',
        'pytest',
        'IPython',
        'jupyter',
    ],
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
    name='SentinelX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console (GUI-only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build_config\\version_info.txt',  # Windows version metadata
    icon='assets\\icon.ico' if sys.platform == 'win32' else None,  # App icon
)
