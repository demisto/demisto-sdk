import base64
import copy
import glob
import io
import json
import os
import re
import sys
from typing import Dict, List, Tuple, Union

import click
from inflection import dasherize, underscore
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION,
    DEFAULT_IMAGE_PREFIX, DIR_TO_PREFIX, INTEGRATIONS_DIR, SCRIPTS_DIR,
    TYPE_TO_EXTENSION, FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.tools import (LOG_COLORS, arg_to_list,
                                               find_type, get_pack_name,
                                               get_yaml, get_yml_paths_in_dir,
                                               print_color, print_error,
                                               print_warning,
                                               server_version_compare)

PACK_METADATA_PATH = 'pack_metadata.json'
CONTRIBUTOR_DISPLAY_NAME = ' ({} Contribution)'
CONTRIBUTOR_DETAILED_DESC = '### {} Contributed Integration\n' \
                            '#### Integration Author: {}\n' \
                            'Support and maintenance for this integration are provided by the author. ' \
                            'Please use the following contact details:'

CONTRIBUTOR_COMMUNITY_DETAILED_DESC = '### Community Contributed Integration\n ' \
                                      '#### Integration Author: {}\n ' \
                                      'No support or maintenance is provided by the author. Customers are encouraged ' \
                                      'to engage with the user community for questions and guidance at the ' \
                                      '[Cortex XSOAR Live Discussions](https://live.paloaltonetworks.com/' \
                                      't5/cortex-xsoar-discussions/bd-p/Cortex_XSOAR_Discussions).'

CONTRIBUTORS_LIST = ['partner', 'developer', 'community']
COMMUNITY_CONTRIBUTOR = 'community'
INTEGRATIONS_DOCS_REFERENCE = 'https://xsoar.pan.dev/docs/reference/integrations/'
UNSUPPORTED_INPUT_ERR_MSG = 'Unsupported input. Please provide either: ' \
                            '1. a directory of an integration or a script. ' \
                            '2. a path of a GenericModule file.'


class YmlUnifier:

    def __init__(self, input: str, dir_name=INTEGRATIONS_DIR, output: str = '',
                 image_prefix=DEFAULT_IMAGE_PREFIX, force: bool = False):

        directory_name = ''
        # Changing relative path to current abspath fixed problem with default output file name.
        if input == '.':
            input = os.path.abspath(input)
        if not os.path.isdir(input):
            print_error(UNSUPPORTED_INPUT_ERR_MSG)
            sys.exit(1)
        for optional_dir_name in DIR_TO_PREFIX:
            if optional_dir_name in input:
                directory_name = optional_dir_name

        if not directory_name:
            print_error(UNSUPPORTED_INPUT_ERR_MSG)

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
            with io.open(self.yml_path, 'r', encoding='utf8') as yml_file:
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
            if server_version_compare(yml_data.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION), '5.0.0') >= 0:
                raise ValueError(f'Failed: {self.dest_path}. dockerimage45 set for 5.0 and later only')

            yml_unified['fromversion'] = '5.0.0'

            # validate that this is a script/integration which targets both 4.5 and 5.0+.
            if server_version_compare(yml_data.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION), '5.0.0') < 0:
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

    def merge_script_package_to_yml(self, file_name_suffix=None):
        """Merge the various components to create an output yml file
        """
        print("Merging package: {}".format(self.package_path))
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}.yml'.format(DIR_TO_PREFIX[self.dir_name], package_dir_name)

        if file_name_suffix:
            # append suffix to output file name
            output_filename = file_name_suffix.join(os.path.splitext(output_filename))

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
            contributor_type, metadata_data = self.get_contributor_data()

            if self.is_contributor_pack(contributor_type):
                contributor_email = metadata_data.get('email', '')
                contributor_url = metadata_data.get('url', '')
                author = metadata_data.get('author')
                yml_unified = self.add_contributors_support(yml_unified, contributor_type, contributor_email,
                                                            contributor_url, author)

        output_map = self.write_yaml_with_docker(yml_unified, self.yml_data, script_obj)
        unifier_outputs = list(output_map.keys()), self.yml_path, script_path, image_path, desc_path
        print_color(f'Created unified yml: {list(output_map.keys())}', LOG_COLORS.GREEN)

        return unifier_outputs[0]

    def insert_image_to_yml(self, yml_data, yml_unified):
        image_data, found_img_path = self.get_data(self.package_path, "*png")
        if image_data:
            image_data = self.image_prefix + base64.b64encode(image_data).decode('utf-8')

            if yml_data.get('image') and self.use_force is False:
                raise ValueError('Please move the image from the yml to an image file (.png)'
                                 f' in the package: {self.package_path}')

            yml_unified['image'] = image_data
        else:
            click.secho(f'Failed getting image data for {self.package_path}', fg="yellow")

        return yml_unified, found_img_path

    def insert_description_to_yml(self, yml_data, yml_unified):
        desc_data, found_desc_path = self.get_data(self.package_path, '*_description.md')

        if yml_data.get('detaileddescription') and self.use_force is False:
            raise ValueError('Please move the detailed description from the yml to a description file (.md)'
                             f' in the package: {self.package_path}')

        detailed_description = ''
        if desc_data:
            detailed_description = FoldedScalarString(desc_data.decode('utf-8'))

        integration_doc_link = ''
        if '[View Integration Documentation]' not in detailed_description:
            integration_doc_link = self.get_integration_doc_link(yml_data)
        if integration_doc_link:
            if detailed_description:
                detailed_description += '\n\n---\n' + integration_doc_link
            else:
                detailed_description += integration_doc_link
        if detailed_description:
            yml_unified['detaileddescription'] = detailed_description
        return yml_unified, found_desc_path

    def get_data(self, path, extension):
        data_path = glob.glob(os.path.join(path, extension))
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
        if self.package_path.endswith(os.path.join('Scripts', 'CommonServerPython')):
            return os.path.join(self.package_path, 'CommonServerPython.py')
        if self.package_path.endswith(os.path.join('Scripts', 'CommonServerPowerShell')):
            return os.path.join(self.package_path, 'CommonServerPowerShell.ps1')
        if self.package_path.endswith('ApiModule'):
            return os.path.join(self.package_path, os.path.basename(os.path.normpath(self.package_path)) + '.py')

        script_path = list(filter(lambda x: not re.search(ignore_regex, x, flags=re.IGNORECASE),
                                  sorted(glob.glob(os.path.join(self.package_path, '*' + script_type)))))[0]

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
        elif script_type == '.ps1':
            clean_code = self.clean_pwsh_code(script_code)
        else:
            # for JS scripts
            clean_code = script_code

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

        if find_type(yml_path) in (FileType.SCRIPT, FileType.TEST_SCRIPT):
            code_type = get_yaml(yml_path).get('type')
        else:
            code_type = get_yaml(yml_path).get('script', {}).get('type')
        unifier = YmlUnifier(self.package_path)
        code_path = unifier.get_code_file(TYPE_TO_EXTENSION[code_type])
        with io.open(code_path, 'r', encoding='utf-8') as code_file:
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
        module_code = YmlUnifier._get_api_module_code(module_name, module_path)

        module_code = f'\n### GENERATED CODE ###\n' \
                      f'# {module_import}\n' \
                      f'# This code was inserted in place of an API module.{module_code}\n' \
                      f'### END GENERATED CODE ###'

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
        # we use '[ \t]' and not \s as we don't want to match newline
        script_code = re.sub(r'import demistomock as demisto[ \t]*(#.*)?', "", script_code)
        script_code = re.sub(r'from CommonServerPython import \*[ \t]*(#.*)?', "", script_code)
        script_code = re.sub(r'from CommonServerUserPython import \*[ \t]*(#.*)?', "", script_code)
        # print function is imported in python loop
        if remove_print_future:  # docs generation requires to leave this
            script_code = re.sub(r'from __future__ import print_function[ \t]*(#.*)?', "", script_code)
        return script_code

    @staticmethod
    def clean_pwsh_code(script_code):
        script_code = script_code.replace(". $PSScriptRoot\\demistomock.ps1", "")
        script_code = script_code.replace(". $PSScriptRoot\\CommonServerPowerShell.ps1", "")
        return script_code

    def get_pack_path(self):
        return self.package_path.split('Integrations')[0]

    def is_contributor_pack(self, contributor_type):
        """Checks if the pack is a contribution.
        Args:
            contributor_type (str): The contributor type.
        Returns:
            (bool). True if it is a contributed pack, False otherwise.
        """
        if contributor_type in CONTRIBUTORS_LIST:
            return True
        return False

    def get_contributor_data(self):
        """Gets contributor data.

        Returns:
            (str, dict). Contributor type and file data.
        """
        pack_path = self.get_pack_path()
        pack_metadata_data, pack_metadata_path = self.get_data(pack_path, PACK_METADATA_PATH)

        if pack_metadata_data:
            try:
                json_pack_metadata = json.loads(pack_metadata_data)
            except json.JSONDecodeError as e:
                pack_name: str = get_pack_name(pack_path)
                raise Exception(f'Failed to load pack metadata of pack {pack_name}: {str(e)}') from e
            support_field = json_pack_metadata.get('support')
            return support_field, json_pack_metadata
        return None, None

    def add_contributors_support(self, unified_yml: Dict, contributor_type: str,
                                 contributor_email: Union[str, List[str]],
                                 contributor_url: str, author: str = '') -> Dict:
        """Add contributor support to the unified file - text in the display name and detailed description.

        Args:
            unified_yml (dict): The unified yaml file.
            contributor_type (str): The contributor type - partner / developer / community
            contributor_email (str): The contributor email.
            contributor_url (str): The contributor url.
            author (str): The packs author.

        Returns:
            The unified yaml file (dict).
        """
        if ' Contribution)' not in unified_yml['display']:
            unified_yml['display'] += CONTRIBUTOR_DISPLAY_NAME.format(contributor_type.capitalize())
        existing_detailed_description = unified_yml.get('detaileddescription', '')
        if contributor_type == COMMUNITY_CONTRIBUTOR:
            contributor_description = CONTRIBUTOR_COMMUNITY_DETAILED_DESC.format(author)
        else:
            contributor_description = CONTRIBUTOR_DETAILED_DESC.format(contributor_type.capitalize(), author)
            if contributor_email:
                email_list: List[str] = arg_to_list(contributor_email, ",")
                for email in email_list:
                    contributor_description += f'\n- **Email**: [{email}](mailto:{email})'
            if contributor_url:
                contributor_description += f'\n- **URL**: [{contributor_url}]({contributor_url})'

        contrib_details = re.findall(r'### .* Contributed Integration', existing_detailed_description)

        if not contrib_details:
            unified_yml['detaileddescription'] = contributor_description + '\n***\n' + existing_detailed_description

        return unified_yml

    def get_integration_doc_link(self, unified_yml: Dict) -> str:
        """Generates the integration link to the integration documentation

        Args:
            unified_yml (Dict): The integration YAML dictionary object

        Returns:
            str: The integration doc markdown link to add to the detailed description (if reachable)
        """
        normalized_integration_id = self.normalize_integration_id(unified_yml['commonfields']['id'])
        integration_doc_link = INTEGRATIONS_DOCS_REFERENCE + normalized_integration_id

        readme_path = os.path.join(self.package_path, 'README.md')
        if os.path.isfile(readme_path) and os.stat(readme_path).st_size != 0:
            # verify README file exists and is not empty
            return f'[View Integration Documentation]({integration_doc_link})'
        else:
            click.secho(
                f'Did not find README in {self.package_path}, not adding integration doc link',
                fg="bright_cyan"
            )
            return ''

    @staticmethod
    def normalize_integration_id(integration_id: str) -> str:
        """Normalizes integration ID to an identifier to be used as the integration documentation ID

        Examples
            >>> normalize_integration_id('Cortex XDR - IOC')
            cortex-xdr---ioc
            >>> normalize_integration_id('Whois')
            whois
            >>> normalize_integration_id('SomeIntegration')
            some-integration

        Args:
            integration_id (str): The integration ID to normalize

        Returns:
            str: The normalized identifier
        """
        dasherized_integration_id = dasherize(underscore(integration_id)).replace(' ', '-')
        # remove all non-word characters (dash is ok)
        return re.sub(r'[^\w-]', '', dasherized_integration_id)
