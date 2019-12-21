#!/usr/bin/env python3.7

# DemistoSDK
# Python client that invokes functions in the Demisto SDK.
#
# Author:       Demisto
# Version:      0.1.8
#

import sys

from demisto_sdk.common.tools import print_color, LOG_COLORS
from demisto_sdk.dev_tools.linter import Linter
from demisto_sdk.validation.secrets import SecretsValidator

class DemistoSDK:
    """
    The core class for the SDK.
    """
    SCRIPT = 'script'
    INTEGRATION = 'integration'

    def __init__(self):
        self.configuration = None

    def initialize_parsers(self):
        Linter.add_sub_parser(self.subparsers)
        SecretsValidator.add_sub_parser(self.subparsers)

    #         elif args.command == 'lint':
    #             return self.lint(args.dir, no_pylint=args.no_pylint, no_flake8=args.no_flake8, no_mypy=args.no_mypy,
    #                              no_bandit=args.no_bandit, no_test=args.no_test, root=args.root,
    #                              keep_container=args.keep_container, verbose=args.verbose, cpu_num=args.cpu_num)
    #
    #         elif args.command == 'secrets':
    #             # returns True is secrets were found
    #             if self.secrets(is_circle=args.circle, white_list_path=args.whitelist):
    #                 return 1

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
