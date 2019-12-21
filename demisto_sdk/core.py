#!/usr/bin/env python3.7

# DemistoSDK
# Python client that invokes functions in the Demisto SDK.
#
# Author:       Demisto
# Version:      0.1.8
#

from demisto_sdk.dev_tools.linter import Linter


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

    #         elif args.command == 'lint':
    #             return self.lint(args.dir, no_pylint=args.no_pylint, no_flake8=args.no_flake8, no_mypy=args.no_mypy,
    #                              no_bandit=args.no_bandit, no_test=args.no_test, root=args.root,
    #                              keep_container=args.keep_container, verbose=args.verbose, cpu_num=args.cpu_num)
    #

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
