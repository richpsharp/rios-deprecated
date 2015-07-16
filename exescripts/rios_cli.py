"""a script that wraps up calls to launch the various user
    interfacesof RIOS"""

import sys
import argparse
import importlib

import natcap.rios

MODEL_LIST = {
    'rios_ipa': "RIOS Investment Portfolio Adviser",
    'rios_porter': "RIOS Portfolio Translator"
    }

def _print_models():
    print 'Available models'
    for model_name, model_description in MODEL_LIST.iteritems():
        print '\t' + model_name + ': ' + model_description

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
        _print_models()
        return

    if args.model not in MODEL_LIST:
        print 'Error: "%s" not a known model.' % args.model
        _print_models()
        model = raw_input('Choose a model: ')
    else:
        model = args.model

    #Otherwise import the module and launch the ui
    importlib.import_module('natcap.rios.rui.' + model).launch_ui(sys.argv)


if __name__ == '__main__':
    main()
