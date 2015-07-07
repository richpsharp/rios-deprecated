"""RIOS setup.py script"""
from setuptools import setup

VERSION = '0.0.1a1'

REQUIREMENTS = [
    'numpy',
    'scipy',
    'gdal',
    'pygeoprocessing==0.3.0a3',
    'pyqt4',
    ]

setup(
    name='natcap.rios',
    version=VERSION,
    package_dir={'natcap': 'src/natcap'},
    namespace_packages=['natcap'],
    packages=[
        'natcap',
        'natcap.rios',
        'natcap.rios.iui',
        'natcap.rios.iui.dbfpy',
        'natcap.rios.iui.jsonschema',
    ],
    install_requires=REQUIREMENTS
)
