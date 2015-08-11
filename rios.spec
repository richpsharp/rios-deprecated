# -*- mode: python -*-
import glob
import os

import shapely #so we can get shapely's dll
import natcap.rios #so we can get the version

DEST_DIRECTORY = 'rios_dest'

HIDDENIMPORTS = [
  'scipy.linalg.cython_blas',
  'scipy.linalg.cython_lapack',
  'scipy.special._ufuncs_cxx',
  'scipy.sparse.linalg.dsolve._superlu',
  'pygeoprocessing.version',
]

SCRIPT = 'exescripts/rios_cli.py'

CURRENT_DIR = os.path.join(os.getcwd(), os.path.dirname(sys.argv[1]))

a = Analysis(
  [SCRIPT],
  pathex=[],
  hiddenimports=HIDDENIMPORTS,
  hookspath=[os.path.join(CURRENT_DIR, 'exescripts', 'hooks')],
  runtime_hooks=None)

a.datas += [('.', 'installer/windows/RIOS-2-square.ico', 'DATA')]
pyz = PYZ(a.pure)
exe = EXE(
  pyz,
  a.binaries + [
      ('geos_c.dll', os.path.join(shapely.__path__[0], 'DLLs', 'geos_c.dll'), 'BINARY'),
      ('msvcp90.dll', 'C:\\Windows\\System32\\msvcp90.dll', 'BINARY'),
      ('msvcr90.dll', 'C:\\Windows\\System32\\msvcr90.dll', 'BINARY'),
  ] if is_win else a.binaries,
  a.scripts,
  name='rios_cli_%s.exe' % natcap.rios.__version__,
  exclude_binaries=True,
  debug=False,
  strip=None,
  upx=True,
  console=True,
  icon='installer/windows/RIOS-2-square.ico')

args = [exe, a.binaries, a.zipfiles, a.datas]

coll = COLLECT(
  *args,
  name=DEST_DIRECTORY,
  strip=None,
  upx=True)
