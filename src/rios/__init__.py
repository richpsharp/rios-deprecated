import versioning
import sys

# The __version__ attribute MUST be set to 'dev'.  It is changed automatically
# when the package is built.  The build_attrs attribute is set at the same time
# but it instead contains a list of attributes of __init__.py that are related
# to the build.
__version__ = '1.1.3'
build_data = ['release', 'build_id', 'py_arch', 'version_str']
build_id = '1.1.3'
py_arch = '32bit'
release = '1.1.3'
version_str = '1.1.3'

if __version__ == 'dev' and build_data is None:
    __version__ = versioning.version()
    build_data = versioning.build_data()
    for key, value in sorted(build_data.iteritems()):
        setattr(sys.modules[__name__], key, value)

    del sys.modules[__name__].key
    del sys.modules[__name__].value


def is_release():
    """Check if this is a 'release' of RIOS.  Returns True or False."""
    if __version__.startswith('dev'):
        return False
    return True
