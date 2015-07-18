"""natcap.rios.iui __init__.py module"""

import os
import logging
import platform
import sys
import locale

import natcap.rios

# Set up logging for the modelUI
# I haven't been able to figure out why, but for some reason I have to add a new
# StreamHandler to the LOGGER object for information to be printed to stdout.  I
# can't figure out why this is necessary here and not necessary in our other
# models, where calling `logging.basicConfig` is sufficient.

# Format string and the date format are shared by the basic configuration as
# well as the added streamhandler.
format_string = '%(asctime)s %(name)-5s %(funcName)-5s %(levelname)-5s %(message)s'
date_format = '%m/%d/%Y %H:%M:%S '

# Do the basic configuration of logging here.  This is required in addition to
# adding the streamHandler below.
logging.basicConfig(format=format_string, level=logging.DEBUG,
        datefmt=date_format)

# Create a formatter and streamhandler to format and print messages to stdout.
formatter = logging.Formatter(format_string, date_format)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

def _user_hash():
    """Returns a hash for the user, based on the machine."""
    data = {
        'os': platform.platform(),
        'hostname': platform.node(),
        'userdir': os.path.expanduser('~')
    }
    try:
        md5 = hashlib.md5()
        md5.update(json.dumps(data))
        return md5.hexdigest()
    except:
        return None


def get_ui_logger(name):
    #Get the logging object for this level and add the handler we just created.
    logger = logging.getLogger(name)
#    logger.addHandler(handler)
    return logger

def log_model(model_name, model_version=None):
    """Submit a POST request to the defined URL with the modelname passed in as
    input.  The InVEST version number is also submitted, retrieved from the
    package's resources.

        model_name - a python string of the package version.
        model_version=None - a python string of the model's version.  Defaults
            to None if a model version is not provided.

    returns nothing."""

    path = 'http://ncp-dev.stanford.edu/~invest-logger/log-modelname.php'
    data = {
        'model_name': model_name,
        'invest_release': 'not_invest_rios_instead',
        'user': _user_hash(),
        'system': {
            'os': platform.system(),
            'release': platform.release(),
            'full_platform_string': platform.platform(),
            'fs_encoding': sys.getfilesystemencoding(),
            'preferred_encoding': locale.getdefaultlocale()[1],
            'default_language': locale.getdefaultlocale()[0],
            'python': {
                'version': platform.python_version(),
                'bits': platform.architecture()[0],
            },
        },
    }

    data['model_version'] = natcap.rios.__version__

    try:
        urlopen(Request(path, urlencode(data)))
    except:
        # An exception was thrown, we don't care.
        print 'an exception encountered when logging'
