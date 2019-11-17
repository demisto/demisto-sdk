import argparse
import re

from demisto_sdk.core import DemistoSDK
from demisto_sdk.common.tools import str2bool, run_command, print_color, LOG_COLORS
from demisto_sdk.common.constants import SCRIPT_CHOICE, INTEGRATION_CHOICE
from demisto_sdk.common.configuration import ValidationConfiguration


def main():
    parser = argparse.ArgumentParser(description='Manage your content with the Demisto SDK.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='stuff', dest='command')

    validation_parser = subparsers.add_parser('validate', description='Validate files')
    validation_parser.add_argument('-c', '--circle', type=str2bool, default=False, help='Is CircleCi or not')
    validation_parser.add_argument('-b', '--backward-comp', type=str2bool, default=True,
                                   help='To check backward compatibility.')
    validation_parser.add_argument('-t', '--test-filter', type=str2bool, default=False,
                                   help='Check that tests are valid.')
    validation_parser.add_argument('-p', '--prev-ver', help='Previous branch or SHA1 commit to run checks against.')
    validation_parser.add_argument('-g', '--use-git', type=str2bool, default=True, help='Validate changes using git.')

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
                                choices=[SCRIPT_CHOICE, INTEGRATION_CHOICE], default=None)
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
    elif args.command == 'validate':
        validate_files(args)
    else:
        print('Use demisto_sdk -h for help with the commands.')


def validate_files(args):
    branch_name = ''
    use_git = args.use_git
    if use_git:
        branches = run_command('git branch')
        branch_name_reg = re.search(r'\* (.*)', branches)
        branch_name = branch_name_reg.group(1)

    is_circle = args.circle
    is_backward_check = args.backward_comp
    prev_ver = args.prev_ver

    print_color('Starting validating files structure', LOG_COLORS.GREEN)
    configuration = ValidationConfiguration.create(is_backward_check=is_backward_check, is_circle=is_circle,
                                                   prev_ver=prev_ver, validate_conf_json=False,
                                                   use_git=use_git)
    configuration.append_sys_path()
    sdk = DemistoSDK(configuration)
    if not sdk.validate(branch_name):
        print_color('omg', LOG_COLORS.RED)
