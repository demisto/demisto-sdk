import base64
import copy
import glob
import io
import os
import re
from typing import Tuple

from demisto_sdk.commands.common.constants import (DEFAULT_IMAGE_PREFIX,
                                                   DIR_TO_PREFIX,
                                                   INTEGRATIONS_DIR,
                                                   SCRIPTS_DIR,
                                                   TYPE_TO_EXTENSION)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type, get_yaml,
                                               get_yml_paths_in_dir,
                                               print_color, print_error,
                                               print_warning,
                                               server_version_compare)
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import FoldedScalarString


class Unifier:

    def __init__(self, input: str, dir_name=INTEGRATIONS_DIR, output: str = '',
                 image_prefix=DEFAULT_IMAGE_PREFIX, force: bool = False):

        directory_name = ""
        for optional_dir_name in DIR_TO_PREFIX:
            if optional_dir_name in input:
                directory_name = optional_dir_name

        if not directory_name:
            print_error('You have failed to provide a legal file path, a legal file path '
                        'should contain either Integrations or Scripts directories')

        self.image_prefix = image_prefix
        self.package_path = input
        self.use_force = force
        if self.package_path.endswith(os.sep):
            self.package_path = self.package_path.rstrip(os.sep)

        self.dest_path = output

        yml_paths, self.yml_path = get_yml_paths_in_dir(self.package_path, Errors.no_yml_file(self.package_path))
        for path in yml_paths:
            # The plugin creates a unified YML file for the package.
            # In case this script runs locally and there is a unified YML file in the package we need to ignore it.
            # Also,
            # we don't take the unified file by default because
            # there might be packages that were not created by the plugin.
            if 'unified' not in path and os.path.basename(os.path.dirname(path)) not in [SCRIPTS_DIR, INTEGRATIONS_DIR]:
                self.yml_path = path
                break

        self.ryaml = YAML()
        self.ryaml.preserve_quotes = True
        self.ryaml.width = 50000  # make sure long lines will not break (relevant for code section)
        if self.yml_path:
            with open(self.yml_path, 'r') as yml_file:
                self.yml_data = self.ryaml.load(yml_file)
        else:
            self.yml_data = {}
            print_error(f'No yml found in path: {self.package_path}')

        # script key for scripts is a string.
        # script key for integrations is a dictionary.
        self.is_script_package = isinstance(self.yml_data.get('script'), str)
        self.dir_name = SCRIPTS_DIR if self.is_script_package else dir_name

    def write_yaml_with_docker(self, yml_unified, yml_data, script_obj):
        """Write out the yaml file taking into account the dockerimage45 tag.
        If it is present will create 2 integration files
        One for 4.5 and below and one for 5.0.

        Arguments:
            output_path {str} -- output path
            yml_unified {dict} -- unified yml dict
            yml_data {dict} -- yml object
            script_obj {dict} -- script object

        Returns:
            dict -- dictionary mapping output path to unified data
        """
        output_map = {self.dest_path: yml_unified}
        if 'dockerimage45' in script_obj:
            # we need to split into two files 45 and 50. Current one will be from version 5.0
            if self.is_script_package:  # scripts
                del yml_unified['dockerimage45']
            else:  # integrations
                del yml_unified['script']['dockerimage45']

            yml_unified45 = copy.deepcopy(yml_unified)

            # validate that this is a script/integration which targets both 4.5 and 5.0+.
            if server_version_compare(yml_data.get('fromversion', '0.0.0'), '5.0.0') >= 0:
                raise ValueError(f'Failed: {self.dest_path}. dockerimage45 set for 5.0 and later only')

            yml_unified['fromversion'] = '5.0.0'

            # validate that this is a script/integration which targets both 4.5 and 5.0+.
            if server_version_compare(yml_data.get('toversion', '99.99.99'), '5.0.0') < 0:
                raise ValueError(f'Failed: {self.dest_path}. dockerimage45 set for 4.5 and earlier only')

            yml_unified45['toversion'] = '4.5.9'

            if script_obj.get('dockerimage45'):  # we have a value for dockerimage45 set it as dockerimage
                if self.is_script_package:  # scripts
                    yml_unified45['dockerimage'] = script_obj.get('dockerimage45')
                else:  # integrations
                    yml_unified45['script']['dockerimage'] = script_obj.get('dockerimage45')

            else:  # no value for dockerimage45 remove the dockerimage entry
                del yml_unified45['dockerimage']

            output_path45 = re.sub(r'\.yml$', '_45.yml', self.dest_path)
            output_map = {
                self.dest_path: yml_unified,
                output_path45: yml_unified45,
            }
        for file_path, file_data in output_map.items():
            if os.path.isfile(file_path) and self.use_force is False:
                raise ValueError(f'Output file already exists: {self.dest_path}.'
                                 ' Make sure to remove this file from source control'
                                 ' or rename this package (for example if it is a v2).')

            with io.open(file_path, mode='w', encoding='utf-8') as file_:
                self.ryaml.dump(file_data, file_)

        return output_map

    def merge_script_package_to_yml(self):
        """Merge the various components to create an output yml file
        """
        print("Merging package: {}".format(self.package_path))
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}.yml'.format(DIR_TO_PREFIX[self.dir_name], package_dir_name)

        if self.dest_path:
            self.dest_path = os.path.join(self.dest_path, output_filename)
        else:
            self.dest_path = os.path.join(self.package_path, output_filename)

        script_obj = self.yml_data

        if not self.is_script_package:
            script_obj = self.yml_data['script']
        script_type = TYPE_TO_EXTENSION[script_obj['type']]

        yml_unified = copy.deepcopy(self.yml_data)

        yml_unified, script_path = self.insert_script_to_yml(script_type, yml_unified, self.yml_data)
        image_path = None
        desc_path = None
        if not self.is_script_package:
            yml_unified, image_path = self.insert_image_to_yml(self.yml_data, yml_unified)
            yml_unified, desc_path = self.insert_description_to_yml(self.yml_data, yml_unified)

        output_map = self.write_yaml_with_docker(yml_unified, self.yml_data, script_obj)
        unifier_outputs = list(output_map.keys()), self.yml_path, script_path, image_path, desc_path
        print_color(f'Created unified yml: {list(output_map.keys())}', LOG_COLORS.GREEN)

        return unifier_outputs[0]

    def insert_image_to_yml(self, yml_data, yml_unified):
        image_data, found_img_path = self.get_data("*png")
        image_data = self.image_prefix + base64.b64encode(image_data).decode('utf-8')

        if yml_data.get('image') and self.use_force is False:
            raise ValueError('Please move the image from the yml to an image file (.png)'
                             f' in the package: {self.package_path}')

        yml_unified['image'] = image_data

        return yml_unified, found_img_path

    def insert_description_to_yml(self, yml_data, yml_unified):
        desc_data, found_desc_path = self.get_data('*_description.md')

        if yml_data.get('detaileddescription') and self.use_force is False:
            raise ValueError('Please move the detailed description from the yml to a description file (.md)'
                             f' in the package: {self.package_path}')
        if desc_data:
            yml_unified['detaileddescription'] = FoldedScalarString(desc_data.decode('utf-8'))

        return yml_unified, found_desc_path

    def get_data(self, extension):
        data_path = glob.glob(os.path.join(self.package_path, extension))
        data = None
        found_data_path = None
        if not self.is_script_package and data_path:
            found_data_path = data_path[0]
            with open(found_data_path, 'rb') as data_file:
                data = data_file.read()

        return data, found_data_path

    def get_code_file(self, script_type):
        """Return the first code file in the specified directory path
        :param script_type: script type: .py, .js, .ps1
        :type script_type: str
        :return: path to found code file
        :rtype: str
        """

        ignore_regex = (r'CommonServerPython\.py|CommonServerUserPython\.py|demistomock\.py|_test\.py'
                        r'|conftest\.py|__init__\.py|ApiModule\.py|vulture_whitelist\.py'
                        r'|CommonServerPowerShell\.ps1|CommonServerUserPowerShell\.ps1|demistomock\.ps1|\.Tests\.ps1')
        if self.package_path.endswith('/'):
            self.package_path = self.package_path[:-1]  # remove the last / as we use os.path.join
        if self.package_path.endswith('Scripts/CommonServerPython'):
            return os.path.join(self.package_path, 'CommonServerPython.py')
        if self.package_path.endswith('Scripts/CommonServerPowerShell'):
            return os.path.join(self.package_path, 'CommonServerPowerShell.ps1')
        if self.package_path.endswith('ApiModule'):
            return os.path.join(self.package_path, os.path.basename(os.path.normpath(self.package_path)) + '.py')

        script_path = list(filter(lambda x: not re.search(ignore_regex, x),
                                  glob.glob(os.path.join(self.package_path, '*' + script_type))))[0]

        return script_path

    def insert_script_to_yml(self, script_type, yml_unified, yml_data):
        script_path = self.get_code_file(script_type)
        with io.open(script_path, mode='r', encoding='utf-8') as script_file:
            script_code = script_file.read()

        # Check if the script imports an API module. If it does,
        # the API module code will be pasted in place of the import.
        module_import, module_name = self.check_api_module_imports(script_code)
        if module_import:
            script_code = self.insert_module_code(script_code, module_import, module_name)

        if script_type == '.py':
            clean_code = self.clean_python_code(script_code)
        if script_type == '.ps1':
            clean_code = self.clean_pwsh_code(script_code)

        if self.is_script_package:
            if yml_data.get('script', '') not in ('', '-'):
                print_warning(f'Script section is not empty in package {self.package_path}.'
                              f'It should be blank or a dash(-).')

            yml_unified['script'] = FoldedScalarString(clean_code)

        else:
            if yml_data['script'].get('script', '') not in ('', '-'):
                print_warning(f'Script section is not empty in package {self.package_path}.'
                              f'It should be blank or a dash(-).')

            yml_unified['script']['script'] = FoldedScalarString(clean_code)

        return yml_unified, script_path

    def get_script_or_integration_package_data(self):
        # should be static method
        _, yml_path = get_yml_paths_in_dir(self.package_path, error_msg='')
        if not yml_path:
            raise Exception(f'No yml files found in package path: {self.package_path}. '
                            'Is this really a package dir?')

        if find_type(yml_path) == 'script':
            code_type = get_yaml(yml_path).get('type')
        else:
            code_type = get_yaml(yml_path).get('script', {}).get('type')
        unifier = Unifier(self.package_path)
        code_path = unifier.get_code_file(TYPE_TO_EXTENSION[code_type])
        with open(code_path, 'r') as code_file:
            code = code_file.read()

        return yml_path, code

    @staticmethod
    def check_api_module_imports(script_code: str) -> Tuple[str, str]:
        """
        Checks integration code for API module imports
        :param script_code: The integration code
        :return: The import string and the imported module name
        """

        # General regex to find API module imports, for example: "from MicrosoftApiModule import *  # noqa: E402"
        module_regex = r'from ([\w\d]+ApiModule) import \*(?:  # noqa: E402)?'

        module_match = re.search(module_regex, script_code)
        if module_match:
            return module_match.group(), module_match.group(1)

        return '', ''

    @staticmethod
    def insert_module_code(script_code: str, module_import: str, module_name: str) -> str:
        """
        Inserts API module in place of an import to the module according to the module name
        :param script_code: The integration code
        :param module_import: The module import string to replace
        :param module_name: The module name
        :return: The integration script with the module code appended in place of the import
        """

        module_path = os.path.join('./Packs', 'ApiModules', 'Scripts', module_name, module_name + '.py')
        module_code = Unifier._get_api_module_code(module_name, module_path)

        module_code = '\n### GENERATED CODE ###\n# This code was inserted in place of an API module.{}\n' \
            .format(module_code)

        return script_code.replace(module_import, module_code)

    @staticmethod
    def _get_api_module_code(module_name, module_path):
        """
        Attempts to get the API module code from the ApiModules pack.
        :param module_name: The API module name
        :param module_path: The API module code file path
        :return: The API module code
        """
        try:
            with io.open(module_path, mode='r', encoding='utf-8') as script_file:
                module_code = script_file.read()
        except Exception as exc:
            raise ValueError('Could not retrieve the module [{}] code: {}'.format(module_name, str(exc)))

        return module_code

    @staticmethod
    def clean_python_code(script_code, remove_print_future=True):
        script_code = script_code.replace("import demistomock as demisto", "")
        script_code = script_code.replace("from CommonServerPython import *", "")
        script_code = script_code.replace("from CommonServerUserPython import *", "")
        # print function is imported in python loop
        if remove_print_future:  # docs generation requires to leave this
            script_code = script_code.replace("from __future__ import print_function", "")
        return script_code

    @staticmethod
    def clean_pwsh_code(script_code):
        script_code = script_code.replace(". $PSScriptRoot\\demistomock.ps1", "")
        script_code = script_code.replace(". $PSScriptRoot\\CommonServerPowerShell.ps1", "")
        return script_code
