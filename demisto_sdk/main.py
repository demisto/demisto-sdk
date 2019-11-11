import argparse

from demisto_sdk.core import DemistoSDK
from demisto_sdk.common.tools import str2bool


def main():
    script = 'script'
    integration = 'integration'

    parser = argparse.ArgumentParser(description='Manage your content with the Demisto SDK.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='stuff', dest='command')
    extract_parser = subparsers.add_parser('extract',
                                           help='Extract code, image and description files'
                                                ' from a demisto integration or script yaml file')
    unify_parser = subparsers.add_parser('unify', help='Unify code, image and description files to a single '
                                                       'Demisto yaml file')

    extract_parser.add_argument("-i", "--infile", help="The yml file to extract from", required=True)
    extract_parser.add_argument("-o", "--outfile",
                                help="The output file or dir (if doing migrate) to write the code to", required=True)
    extract_parser.add_argument("-m", "--migrate", action='store_true',
                                help="Migrate an integration to package format."
                                     " Pass to -o option a directory in this case.")
    extract_parser.add_argument("-t", "--type",
                                help="Yaml type. If not specified will try to determine type based upon path.",
                                choices=[script, integration], default=None)
    extract_parser.add_argument("-d", "--demistomock", help="Add an import for demisto mock",
                                choices=[True, False], type=str2bool, default=True)
    extract_parser.add_argument("-c", "--commonserver",
                                help=("Add an import for CommonServerPython. "
                                      " If not specified will import unless this is CommonServerPython"),
                                choices=[True, False], type=str2bool, default=None)

    unify_parser.add_argument("-i", "--indir", help="The path to the files to unify", required=True)
    unify_parser.add_argument("-o", "--outdir", help="The output dir to write the unified yml to", required=True)

    args = parser.parse_args()

    sdk = DemistoSDK()

    if args.command == 'extract':
        if args.migrate:
            sdk.migrate_file(args.infile, args.outfile, args.demistomock, args.commonserver, args.type)
        else:
            sdk.extract_code(args.infile, args.outfile, args.demistomock, args.commonserver, args.type)
    elif args.command == 'unify':
        sdk.unify_package(args.indir, args.outdir)
    else:
        print('Use demisto_sdk -h for help with the commands.')
