# -*- mode: python -*-

block_cipher = None
import os

a = Analysis(['gentle.py'],
             pathex=[os.path.abspath(os.curdir)],
             binaries=None,
             datas=[(X,X) for X in ['www', 'data', 'PROTO_LANGDIR', 'ffmpeg', 'standard_kaldi', 'mkgraph']],
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
          upx=True,
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
             icon='logo.icns',
             bundle_identifier=None)
