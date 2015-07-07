"""RIOS setup.py script"""

import setuptools

VERSION = '0.0.1a1'

REQUIREMENTS = [
    'numpy',
    'scipy',
    'gdal',
    'pygeoprocessing==0.3.0a3',
    'pyqt4',
    ]

setuptools.setup(
    name='natcap.rios',
    version=VERSION,
    package_dir={'natcap': 'src/natcap'},
    namespace_packages=['natcap'],
    include_package_data=True,
    packages=setuptools.find_packages('src'),
    install_requires=REQUIREMENTS,
    package_data={
        'natcap.rios.iui': ['*.png']
    }
)
