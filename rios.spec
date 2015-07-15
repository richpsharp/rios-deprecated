# -*- mode: python -*-
import glob
import os
import shutil

import shapely #so we can get shapely's dll
from PyInstaller.compat import is_win

SCRIPTS = glob.glob('exescripts/*.py')
DEST_DIRECTORY = 'rios_dest'

HIDDENIMPORTS = [
  'natcap.rios',
  'natcap.rios.rios',
  'natcap.rios.disk_sort',
  'natcap.versioner',
  'multiprocessing',
  'multiprocessing.process',
  'multiprocessing.util',
  '_multiprocessing',
  'scipy.linalg.cython_blas',
  'scipy.linalg.cython_lapack',
  'scipy.special._ufuncs',
  'scipy.special._ufuncs_cxx',
]

analysis_object_tuples = []
for script in SCRIPTS:
  basename = os.path.splitext(os.path.basename(script))[0]
  a = Analysis(
    [script],
    pathex=[],
    hiddenimports=HIDDENIMPORTS,
    hookspath=None,
    runtime_hooks=None)
  analysis_object_tuples.append((a, basename, basename+'.exe'))

MERGE(*analysis_object_tuples)

exe_objects = []
binaries = []
zipfiles = []
datas = []

for a, basename, basename_exe in analysis_object_tuples:
  #Get the IUI json files and icons
  for suffix in ['*.png', '*.json']:
    a.datas += [
      ((os.path.join('natcap/rios/iui', os.path.basename(x))),x,'DATA')
      for x in glob.glob('src/natcap/rios/iui/' + suffix)]

  #pick up the report style sheet
  a.datas += [
    ('natcap/rios/report_style.css',
    'src/natcap/rios/report_style.css', 'DATA')]

  a.datas += [('.', 'installer/windows/RIOS-2-square.ico', 'DATA')]

  pyz = PYZ(a.pure)

  exe = EXE(
    pyz,
    a.binaries + [
        ('geos_c.dll', os.path.join(shapely.__path__, 'geos_c.dll', 'BINARY')),
        ('msvcp90.dll', 'C:\\Windows\\System32\\msvcp90.dll', 'BINARY'),
        ('msvcr90.dll', 'C:\\Windows\\System32\\msvcr90.dll', 'BINARY'),
    ] if is_win else a.binaries,
    a.scripts,
    name=basename_exe,
    exclude_binaries=True,
    debug=False,
    strip=None,
    upx=False,
    console=True,
    icon='installer/windows/RIOS-2-square.ico')

  exe_objects.append(exe)
  binaries.append(a.binaries)
  zipfiles.append(a.zipfiles)
  datas.append(a.datas)

  print script

args = exe_objects + binaries + zipfiles + datas

coll = COLLECT(
        *args,
        name=DEST_DIRECTORY,
        strip=None,
        upx=False)
