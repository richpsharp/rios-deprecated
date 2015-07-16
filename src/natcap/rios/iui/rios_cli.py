"""a script that wraps up calls to launch the various user
    interfacesof RIOS"""

import sys
import argparse

import natcap.rios
import natcap.rios.iui.rios_ipa
import natcap.rios.iui.rios_porter

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
        help='The model to run.  Use --list to show available models/tools.')

    args = parser.parse_args()

    if args.list:
        print 'Available models:'
        for model_name, model_description in MODEL_LIST.iteritems():
            print model_name + ': ' + model_description
        return

    if args.model not in MODEL_LIST:
        print (
            'Error: "%s" not a known model. Use --list to show available '
            'models.' % args.model)
        return 1

    if args.model == 'rios_ipa':
        natcap.rios.iui.rios_ipa.launch_ui(sys.argv)

    if args.model == 'rios_porter':
        natcap.rios.iui.rios_porter.launch_ui(sys.argv)

if __name__ == '__main__':
    main()
