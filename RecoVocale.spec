# -*- mode: python ; coding: utf-8 -*-

print(">>> USING CUSTOM SPEC FILE <<<")

from PyInstaller.utils.hooks import collect_all

# Récupérer modules + datas
datas_p, binaries_p, hiddenimports_p = collect_all('phonemizer')
datas_lt, binaries_lt, hiddenimports_lt = collect_all('language_tags')

EXTRA_DATAS = [
    ('srcs/Icons', 'Icons'),
    ('srcs/config', 'config'),
]
EXTRA_HIDDEN = [
    'scipy.io',
    # renfort explicite espeak backend (parfois utile)
    'phonemizer.backend',
    'phonemizer.backend.espeak',
    'phonemizer.backend.espeak.base',
    'phonemizer.backend.espeak.espeak',
]

a = Analysis(
    ['srcs\\RecoVocale.py'],
    pathex=[],
    binaries=binaries_p + binaries_lt,
    datas=EXTRA_DATAS + datas_p + datas_lt,
    hiddenimports=EXTRA_HIDDEN + hiddenimports_p + hiddenimports_lt,
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
    a.binaries,
    a.datas,
    [],
    name='RecoVocale',
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
    version='version_info.txt',
    icon=['reco.ico'],
)
