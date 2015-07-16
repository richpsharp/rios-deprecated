"""a script that wraps up calls to launch the various user
    interfacesof RIOS"""

import sys
import argparse
import importlib

import natcap.versioner
import natcap.rios

MODEL_LIST = {
    'rios_ipa': "RIOS Investment Portfolio Adviser",
    'rios_porter': "RIOS Portfolio Translator"
    }

def main():
    """
    Single entry point for all RIOS UIs
    """

    parser = argparse.ArgumentParser(description="RIOS entry point")
    parser.add_argument(
        '--version', action='version', version=natcap.rios.__version__)
    parser.add_argument(
        '--list', action='store_true', help='List available models')
    parser.add_argument(
        'model', nargs='?',
        help='The model to run.')

    args = parser.parse_args()

    if args.list:
        print 'Available models'
        for model_name, model_description in MODEL_LIST.iteritems():
            print '\t' + model_name + ': ' + model_description
        return

    if args.model not in MODEL_LIST:
        print (
            'Error: "%s" not a known model. Use --list to show available '
            'models.' % args.model)
        return 1

    #Otherwise import the module and launch the ui
    importlib.import_module('natcap.rios.iui.' + args.model).launch_ui(sys.argv)


if __name__ == '__main__':
    main()
