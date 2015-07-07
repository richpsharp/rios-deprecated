"""RIOS setup.py script"""

import platform
import os
import sys
import glob
import zipfile
import shutil
import subprocess
from distutils.core import setup
from distutils.core import Command
from distutils.extension import Extension
import distutils.sysconfig as sysconfig

import numpy
from Cython.Distutils import build_ext

import rios

# write the version attributes to the RIOS __init__ file.
rios.versioning.write_build_info('rios/__init__.py')

from rios import __version__ as VERSION
from rios import image_utils

SITE_PACKAGES = sysconfig.get_python_lib()

# Make custom setup command to build NSIS installer using predefined NSIS
# script.
class NSISCommand(Command):
    """Uses two options: "version" : the rios version; "nsis_dir" : the
    installation directory containing the py2exe executeables to be packaged
    up."""
    description = "Custom command to build our NSIS installer."

    # This list of tuples allows for command-line options for this distutils
    # command.
    user_options = [
        ('nsis-dir=', None, 'Folder with executeables to compress.'),
        ('nsis-install=', None, 'Location of the NSIS installation on disk')]

    def initialize_options(self):
        self.nsis_dir = None
        self.nsis_install = None

    def finalize_options(self):
        pass

    def run(self):
        # Extract the version from the given build directory by switching into
        # the built directory so we can get at the built RIOS.
        cwd = os.getcwd()  # current working directory
        os.chdir(os.path.join(self.nsis_dir, 'rios_data'))
        from rios import __version__ as version
        os.chdir(cwd)  # Pop back to the rios root.

        # Build the installer's splash screen based on the RIOS version no.
        image_utils.write_splash_screen(
          'installer/RIOS_splash.jpg', 'installer/Ubuntu-R.ttf', version,
          'installer/RIOS_splash_v.jpg')

        # Check whether the specified folder to compress exists on disk.  If
        # not, exit this function because NSIS will happily compile without the
        # RIOS_data directory.
        rios_data_dir = os.path.join(self.nsis_dir, 'rios_data')
        if not os.path.exists(rios_data_dir):
            print str(
                'The directory %s/rios_data does not exist.'
                '  Did you run Py2exe?') % self.nsis_dir
            return

        # Run the make_nsis command
        program_path = []

        # If the user provided a local NSIS install path, check that it exists
        # before using it.  If it doesn't exist, check the usual places,
        # according to the OS.
        if self.nsis_install != None:
            if os.path.exists(self.nsis_install):
                makensis_path = self.nsis_install
            else:
                makensis_path = ''
                print str(
                  'ERROR: "%s" does not exist.' % self.nsis_install +
                  ' Checking the usual place(s) on this computer instead')
        if program_path == []:
            if platform.system() == 'Windows':
                possible_paths = ['C:/Program Files/NSIS/makensis.exe',
                                  'C:/Program Files (x86)/NSIS/makensis.exe']
                for path in possible_paths:
                    if os.path.isfile(path):
                        makensis_path = path
                        break
            else:
                program_path = ['wine']

                # The call to makensis requires that the user path be fully
                # qualified and that the program files path be un-escaped.
                makensis_path = os.path.expanduser(
                  '~/.wine/drive_c/Program Files/NSIS/makensis.exe')

        # sanitize the version string for windows compatibility
        version = version.replace(':', '').replace(' ', '_')
        command = ['/DVERSION=%s' % version,
                   '/DPY2EXE_FOLDER=%s' % self.nsis_dir,
                   '/DARCHITECTURE=x86',
                   'installer/rios_full_install_build.nsi']

        subprocess.call(program_path + [makensis_path] + command)


class ZipCommand(Command):
    description = 'Custom command to recurseively zip a folder'
    user_options = [
        ('zip-dir=', None, 'Folder to be zipped up'),
        ('zip-file=', None, 'Output zip file path')]

    def initialize_options(self):
        self.zip_dir = None
        self.zip_file = None

    def finalize_options(self):
        """This function, though empty, is requred to exist in subclasses of
        Command."""
        pass

    def run(self):
        zip = zipfile.ZipFile(self.zip_file, 'w',
            compression=zipfile.ZIP_DEFLATED)
        dir = self.zip_dir
        print dir
        for root, dirs, files in os.walk(dir):
            for f in files:
                fullpath = os.path.join(root, f)
                print(fullpath)
                zip.write(fullpath, fullpath, zipfile.ZIP_DEFLATED)
        zip.close()


options = {}
console = []
data_files = []

for file_name in glob.glob('*.json') + glob.glob('*.csv'):
    data_files.append(('.', [file_name]))

iui_dir = os.path.join('invest-natcap.invest-3', 'invest_natcap', 'iui')
icon_names = ['dialog-close', 'dialog-ok', 'document-open', 'edit-undo',
              'info', 'natcap_logo', 'validate-pass', 'validate-fail',
              'dialog-warning', 'dialog-warning-big', 'dialog-information-2',
              'dialog-error', 'list-remove']
iui_icons = []
for name in icon_names:
    iui_icons.append(os.path.join(iui_dir, '%s.png' % name))

PYTHON_VERSION = 'python%s' % '.'.join(
    [str(r) for r in sys.version_info[:2]])
IUI_ICON_PATH = os.path.join('invest_natcap', 'iui')
data_files.append((IUI_ICON_PATH, iui_icons))

data_files.append(
    (os.path.join(SITE_PACKAGES, 'rios'), ['rios/report_style.css']))

DIST_DIR = 'rios_' + VERSION.replace('.', '_').replace(':', '_')
rios_data = os.path.join(DIST_DIR, 'rios_data')

packages = [
    'rios',
    'invest_natcap',
    'invest_natcap.dbfpy',
    'invest_natcap.iui',
    'invest_natcap.iui.dbfpy',
]

if platform.system() == 'Windows':
    import py2exe
    options = {
        "py2exe": {
            "includes": ["sip",
                         "scipy.io.matlab.streams",
                         "scipy.sparse.csgraph._validation",
                         'rios_ipa',
                         'rios_porter',
                         "rios",
                         "rios.disk_sort",
                         "rios.rios_core",
                         'invest_natcap',
                         'scipy.io.matlab.streams',
                         'scipy.special',
                         'ctypes',
                         'shapely.geos',
                         'matplotlib.backends.backend_qt4agg',
                         'scipy.special._ufuncs_cxx',
                        ],
            'dist_dir': rios_data,
            'packages': packages,
            "skip_archive": True,
            },
        "build_installer": {"nsis_dir": DIST_DIR}
        }

    # Add details about py2exe console files including the file and the
    # application icon.
    console = [{'script': 'rios_ipa.py',
                'icon_resources': [(0, 'installer/RIOS-2-square.ico')],
                'dest_base': 'rios_ipa'},
               {'script': 'rios_porter.py',
                'icon_resources': [(0, 'installer/RIOS-2-square.ico')],
                'dest_base': 'rios_porter'}]

    # Add the rios launch batch script to the root folder, up one level from
    # the distribution folder.
    data_files.append((
        '..', ['ipa_rios.bat', 'porter_rios.bat', 'LICENSE.txt']))
    data_files.append(
        ('.', glob.glob('invest-natcap.invest-3/gdal_dlls/*.dll')))
    data_files.append(('.', ['geos_c.dll']))

    # include the IUI icons in two places.  the site-packages folder is
    # necessary for when bootstrapping RIOS from the command line.  The current
    # dir folder is necessary for Py2exe.
    data_files.append(('lib/site-packages/invest_natcap/iui', iui_icons))
    data_files.append(('invest_natcap/iui', iui_icons))

    # add needed window icons and CSS.
    data_files.append(('.', ['installer/RIOS-2.ico',
                             'installer/RIOS-2-square.ico']))

    DLL_DIR = 'dll/'
    sys.path = [DLL_DIR] + sys.path

    #include whole directories
    for directory in ['rios', 'report_template', 'OSGeo4W']:
        for root_dir, sub_folders, file_list in os.walk(directory):
            data_files.append((
                root_dir, [os.path.join(root_dir, x) for x in file_list]))
    #Copy over the preprocessing toolkit
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.copytree('arc_utils', DIST_DIR)


# Use the determined virtualenv site-packages path to add all files in the
# IUI resources directory to our setup.py data files.  On windows, the LIB_PATH
# should be '', so stuff will be copied to the dest_dir.
# The dest_dir is the same path that's passed in to the loop as 'directory',
# just with trim number of directory levels chopped off the front.
for directory, trim in [
        ('invest-natcap.invest-3/invest_natcap/iui/iui_resources', 2),
        ('rios_resources', 0)]:
    for root_dir, sub_folders, file_list in os.walk(directory):
        dest_dir = os.sep.join(root_dir.split('/')[trim:])
        data_files.append((
            dest_dir, [os.path.join(root_dir, x) for x in file_list]))

# Add options for the Zip command we create above.  These options are not used
# unless the user calls 'python setup.py zip' and can be overridden at the
# command line anyways if alterations are desired.
options['zip'] = {
    'zip_file': "%s.zip" % DIST_DIR,
    'zip_dir': DIST_DIR
}

REQUIRES_LIST = [
    'pygeoprocessing (>=0.2.0)',
    'osgeo (>=1.9.2)',
]
print data_files
setup(
    name='rios',
    version=VERSION,
    packages=packages,
    requires=REQUIRES_LIST,
    include_dirs=[numpy.get_include()],
    cmdclass={'build_installer': NSISCommand,
              'zip': ZipCommand,
              'build_ext': build_ext},
    package_dir={'invest_natcap':
                 'invest-natcap.invest-3/invest_natcap'},
    console=console,
    data_files=data_files,
    ext_modules=[Extension(name="rios_cython_core",
                           sources=['rios/rios_cython_core.pyx']),
                 Extension(name="routing_cython_core",
                           sources=['invest-natcap.invest-3/invest_natcap/routing/routing_cython_core.pyx'],
                             language="c++"),
                 Extension(name="raster_cython_utils",
                           sources=['invest-natcap.invest-3/invest_natcap/raster_cython_utils.pyx'],
                           language="c++"),
                 Extension(name="invest_cython_core",
                           sources=['invest-natcap.invest-3/invest_natcap/cython_modules/invest_cython_core.pyx',
                                    'invest-natcap.invest-3/invest_natcap/cython_modules/simplequeue.c'])],
    options=options)
