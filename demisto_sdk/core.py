#!/usr/bin/env python3.7

# DemistoSDK
# Python client that invokes functions in the Demisto SDK.
#
# Author:       Demisto
# Version:      0.1.8
#

import sys
import json
import argparse
from pkg_resources import get_distribution

from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.constants import DIR_TO_PREFIX
from demisto_sdk.common.tools import print_color, print_error, LOG_COLORS
from demisto_sdk.dev_tools.linter import Linter
from demisto_sdk.validation.file_validator import FilesValidator
from demisto_sdk.validation.secrets import SecretsValidator
from demisto_sdk.yaml_tools.content_creator import ContentCreator
from demisto_sdk.yaml_tools.extractor import Extractor
from demisto_sdk.yaml_tools.unifier import Unifier


class DemistoSDK:
    """
    The core class for the SDK.
    """
    SCRIPT = 'script'
    INTEGRATION = 'integration'

    def __init__(self):
        self.configuration = None

    def initialize_parsers(self):
        FilesValidator.add_sub_parser(self.subparsers)
        Linter.add_sub_parser(self.subparsers)
        SecretsValidator.add_sub_parser(self.subparsers)
        ContentCreator.add_sub_parser(self.subparsers)

    # def parse_args(self):
    #     args = self.parser.parse_args()
    #
    #     try:
    #         elif args.command == 'validate':
    #
    #             if self.validate(is_backward_check=args.backward_comp, is_circle=args.circle,
    #                              prev_ver=args.prev_ver, validate_conf_json=args.conf_json, use_git=args.use_git):
    #                 print_color('The files are valid', LOG_COLORS.GREEN)
    #
    #             else:
    #                 print_color('The files are invalid', LOG_COLORS.RED)
    #                 return 1
    #
    #         elif args.command == 'lint':
    #             return self.lint(args.dir, no_pylint=args.no_pylint, no_flake8=args.no_flake8, no_mypy=args.no_mypy,
    #                              no_bandit=args.no_bandit, no_test=args.no_test, root=args.root,
    #                              keep_container=args.keep_container, verbose=args.verbose, cpu_num=args.cpu_num)
    #
    #         elif args.command == 'secrets':
    #             # returns True is secrets were found
    #             if self.secrets(is_circle=args.circle, white_list_path=args.whitelist):
    #                 return 1
    #
    #         elif args.command == 'create':
    #             self.create_content_artifacts(args.artifacts_path, args.preserve_bundles)
    #
    #         else:
    #             print('Use demisto-sdk -h to see the available commands.')
    #
    #         return 0
    #
    #     except Exception as e:
    #         print_error('Error! The operation [{}] failed: {}'.format(args.command, str(e)))
    #         return 1

    def validate(self, **kwargs):
        sys.path.append(self.configuration.env_dir)

        print_color('Starting validating files structure', LOG_COLORS.GREEN)

        validator = FilesValidator(configuration=self.configuration, **kwargs)

        return validator.is_valid_structure()

    def lint(self, project_dir: str, **kwargs):
        """
        Run lint on python code in a provided directory.
        :param project_dir The directory containing the code.
        :param kwargs Optional arguments.
        :return: The lint result.
        """
        linter = Linter(configuration=self.configuration, project_dir=project_dir, **kwargs)
        ans = linter.run_dev_packages()
        return ans

    def secrets(self, **kwargs):
        sys.path.append(self.configuration.env_dir)

        print_color('Starting secrets detection', LOG_COLORS.GREEN)

        validator = SecretsValidator(configuration=self.configuration, **kwargs)

        return validator.find_secrets()

    @staticmethod
    def create_content_artifacts(self, artifact_path, preserve_bundles):
        cc = ContentCreator(artifact_path, preserve_bundles=preserve_bundles)
        cc.create_content()
        if cc.long_file_names:
            print_error(f'The following files exceeded to file name length limit of {cc.file_name_max_size}:\n'
                        f'{json.dumps(cc.long_file_names, indent=4)}')
