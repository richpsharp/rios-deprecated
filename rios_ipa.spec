# -*- mode: python -*-
import glob

from PyInstaller.compat import is_win

a = Analysis(['rios_ipa.py'],
             pathex=[],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

#Get the IUI json files and icons
for suffix in ['*.png', '*.json']:
  a.datas += [
    ((os.path.join('natcap/rios/iui', os.path.basename(x))),x,'DATA')
    for x in glob.glob('src/natcap/rios/iui/' + suffix)]

#pick up the report style sheet
a.datas += [
  ('natcap/rios/report_style.css',
  'src/natcap/rios/report_style.css', 'DATA')]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.binaries + [
              ('msvcp90.dll', 'C:\\Windows\\System32\\msvcp90.dll', 'BINARY'),
              ('msvcr90.dll', 'C:\\Windows\\System32\\msvcr90.dll', 'BINARY')
          ] if is_win else a.binaries,
          a.scripts,
          exclude_binaries=True,
          name='rios_ipa.exe',
          debug=False,
          strip=None,
          upx=False,
          console=True )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=False,
               name='rios_ipa')
