# -*- mode: python -*-
a = Analysis(['rios_ipa.py'],
             pathex=['C:\\Users\\Rich\\Documents\\natcap-rios\\exescripts'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

import glob

#Get the IUI json files and icons
for suffix in ['*.png', '*.json']:
  a.datas += [
    ((os.path.join('natcap/rios/iui', os.path.basename(x))),x,'DATA')
    for x in glob.glob('../src/natcap/rios/iui/' + suffix)]

#pick up the report style sheet
a.datas += [
  ('natcap/rios/report_style.css',
  '../src/natcap/rios/report_style.css', 'DATA')]

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.binaries,
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
