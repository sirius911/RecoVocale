# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['srcs/RecoVocale.py'],
             pathex=['.'],
             binaries=[],
             datas=[('srcs/Icons', 'Icons'), ('srcs/config', 'config')],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='RecoVocale',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='reco.ico',
          version='version_file.txt')  # Ajout du fichier version ici

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='RecoVocale')
