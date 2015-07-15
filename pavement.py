"""RIOS pavement.py script"""

import os
import sys
import subprocess

from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import paver.easy
import paver.setuputils
from paver.setuputils import setup
import PyInstaller.main
import natcap.versioner

VERSION = natcap.versioner.parse_version()

REQUIREMENTS = [
    'numpy',
    'scipy>=0.13.0',
    'gdal',
    'pygeoprocessing==0.3.0a3',
    'pyqt4',
    ]

setup(
    name='natcap.rios',
    packages=paver.setuputils.find_packages('src'),
    version=VERSION,
    natcap_version='src/natcap/rios/version.py',
    url="https://bitbucket.org/natcap/rios",
    author="Rich Sharp",
    author_email="richpsharp@gmail.com",
    package_dir={'natcap': 'src/natcap'},
    namespace_packages=['natcap'],
    install_requires=REQUIREMENTS,
    package_data={
        'natcap.rios.iui': ['*.png', '*.json'],
        'natcap.rios': ['report_style.css']
    }
)

@paver.easy.task
@paver.easy.needs('paver.setuputils.install')
def make_frozen_exe():
    """Wrapper to call pyinstaller directly"""
    PyInstaller.main.run(['rios.spec', '--noconfirm'])


@paver.easy.task
@paver.easy.needs('make_frozen_exe')
@paver.easy.cmdopts([
    ('nsis_binary_path=', '-nsis_binary_path', 'Path for NSIS executable')
])
def make_installer(options):
    """Command to build NSIS installer."""
    print options
    nsis_binary_path = options['nsis_binary_path']
    # Build the installer's splash screen based on the RIOS version no.
    _write_splash_screen(
        'installer/windows/RIOS_splash.jpg',
        'installer/windows/Ubuntu-R.ttf', VERSION,
        'installer/windows/RIOS_splash_v.jpg')

    rios_dist_dir = os.path.join('dist', 'rios_dest')

    if not os.path.exists(nsis_binary_path):
        print str('ERROR: "%s" does not exist.' % nsis_binary_path)
        sys.exit(-1)

    # sanitize the version string for windows compatibility
    version = VERSION
    version = version.replace(':', '').replace(' ', '_')
    command = ['/DVERSION=%s' % version,
               '/DDIST_FOLDER=%s' % rios_dist_dir,
               '/DARCHITECTURE=x86',
               'installer/windows/rios_full_install_build.nsi']

    subprocess.call([nsis_binary_path] + command)


def _write_splash_screen(base_image, font_path, version, out_path):
    """Write a simple splash screen by compositing text on top of a base image.

    base_image - a uri to an image
    font_path - a uri to a truetype font file
    version - the version string to write to the splash screen
    out_path - the output path to the finished file

    returns nothing."""

    font = ImageFont.truetype(font_path, 25)
    img = Image.open(base_image)
    draw = ImageDraw.Draw(img)
    draw.text((15, 375), version, (150, 150, 150), font=font)

    draw = ImageDraw.Draw(img)
    img.save(out_path)
