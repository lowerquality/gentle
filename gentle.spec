# -*- mode: python -*-

block_cipher = None
import os

data_files = []
for dirpath in ['www', 'data', 'PROTO_LANGDIR']:
    data_files.append((dirpath, dirpath))
for exepath in ['ffmpeg', 'standard_kaldi', 'mkgraph']:
    data_files.append((exepath, ''))

a = Analysis(['gentle.py'],
             pathex=[os.path.abspath(os.curdir)],
             binaries=None,
             datas=data_files,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='gentle',
          debug=False,
          strip=None,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='gentle')
app = BUNDLE(coll,
             name='gentle.app',
             icon=None,
             bundle_identifier=None,
             info_plist={
                 'NSHighResolutionCapable': 'True'
             },
)
