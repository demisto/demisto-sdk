#!/usr/bin/env python3.7

# DemistoSDK
# Python client that invokes functions in the Demisto SDK.
#
# Author:       Demisto
# Version:      0.1
#

import sys
import argparse

from .common.constants import DIR_TO_PREFIX
from .common.tools import print_color, print_error, LOG_COLORS
from .yaml_tools.unifier import Unifier
from .yaml_tools.extractor import Extractor
from .common.configuration import Configuration
from .validation.file_validator import FilesValidator


class DemistoSDK:
    """
    The core class for the SDK.
    """
    SCRIPT = 'script'
    INTEGRATION = 'integration'

    def __init__(self, configuration=Configuration()):
        self.parser = argparse.ArgumentParser(description='Manage your content with the Demisto SDK.',
                                              formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.subparsers = self.parser.add_subparsers(dest='command')
        self.initialize_parsers()
        self.configuration = configuration

    def initialize_parsers(self):
        Unifier.add_sub_parser(self.subparsers)
        Extractor.add_sub_parser(self.subparsers)
        FilesValidator.add_sub_parser(self.subparsers)

    def parse_args(self):
        args = self.parser.parse_args()
        if args.command == 'extract':
            if args.migrate:
                self.migrate_file(args.infile, args.outfile, args.demistomock, args.commonserver, args.type)
            else:
                self.extract_code(args.infile, args.outfile, args.demistomock, args.commonserver, args.type)
        elif args.command == 'unify':
            self.unify_package(args.indir, args.outdir)
        elif args.command == 'validate':
            if self.validate(is_backward_check=args.backward_comp, is_circle=args.circle,
                             prev_ver=args.prev_ver, validate_conf_json=args.conf_json, use_git=args.use_git):
                print_color('The files are valid', LOG_COLORS.GREEN)
            else:
                print_color('The files are invalid', LOG_COLORS.RED)
        else:
            print('Use demisto-sdk -h to see the available commands.')

    def unify_package(self, package_path, dest_path):
        directory_name = ""
        for dir_name in DIR_TO_PREFIX.keys():
            if dir_name in package_path:
                directory_name = dir_name

        if not directory_name:
            print_error("You have failed to provide a legal file path, a legal file path "
                        "should contain either Integrations or Scripts directories")

        unifier = Unifier(package_path, directory_name, dest_path)
        return unifier.merge_script_package_to_yml()

    def migrate_file(self, yml_path: str, dest_path: str, add_demisto_mock=True, add_common_server=True,
                     yml_type=''):
        extractor = Extractor(yml_path, dest_path, add_demisto_mock, add_common_server, yml_type, self.configuration)
        return extractor.migrate()

    def extract_code(self, yml_path: str, dest_path: str, add_demisto_mock=True, add_common_server=True,
                     yml_type=''):
        extractor = Extractor(yml_path, dest_path, add_demisto_mock, add_common_server, yml_type, self.configuration)
        return extractor.extract_code(dest_path)

    def validate(self, **kwargs):
        sys.path.append(self.configuration.content_dir)

        print_color('Starting validating files structure', LOG_COLORS.GREEN)

        validator = FilesValidator(configuration=self.configuration, **kwargs)

        return validator.is_valid_structure()
