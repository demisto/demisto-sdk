import os
import io
import glob
import yaml
import base64
import re

from demisto_sdk.common.constants import Errors
from demisto_sdk.common.tools import get_yaml, server_version_compare, get_yml_paths_in_dir
from demisto_sdk.common.constants import TYPE_TO_EXTENSION, INTEGRATIONS_DIR, DIR_TO_PREFIX, DEFAULT_IMAGE_PREFIX, \
    SCRIPTS_DIR, BETA_INTEGRATIONS_DIR


class Unifier:

    def __init__(self, package_path: str, dir_name=INTEGRATIONS_DIR, dest_path='', image_prefix=DEFAULT_IMAGE_PREFIX):

        self.image_prefix = image_prefix
        self.package_path = package_path
        if self.package_path[-1] != os.sep:
            self.package_path = os.path.join(self.package_path, '')

        self.dir_name = dir_name
        self.dest_path = dest_path

        self.is_ci = os.getenv('CI', False)

    def write_yaml_with_docker(self, yml_text, yml_data, script_obj):
        """Write out the yaml file taking into account the dockerimage45 tag.
        If it is present will create 2 integration files
        One for 4.5 and below and one for 5.0.

        Arguments:
            output_path {str} -- output path
            yml_text {str} -- yml text
            yml_data {dict} -- yml object
            script_obj {dict} -- script object

        Returns:
            dict -- dictionary mapping output path to text data
        """
        output_map = {self.dest_path: yml_text}
        if 'dockerimage45' in script_obj:
            # we need to split into two files 45 and 50. Current one will be from version 5.0
            yml_text = re.sub(r'^\s*dockerimage45:.*\n?', '', yml_text,
                              flags=re.MULTILINE)  # remove the dockerimage45 line
            yml_text45 = yml_text
            if 'fromversion' in yml_data:
                # validate that this is a script/integration which targets both 4.5 and 5.0+.
                if server_version_compare(yml_data['fromversion'], '5.0.0') >= 0:
                    raise ValueError('Failed: {}. dockerimage45 set for 5.0 and later only'.format(self.dest_path))
                yml_text = re.sub(r'^fromversion:.*$', 'fromversion: 5.0.0', yml_text, flags=re.MULTILINE)
            else:
                yml_text = 'fromversion: 5.0.0\n' + yml_text
            if 'toversion' in yml_data:
                # validate that this is a script/integration which targets both 4.5 and 5.0+.
                if server_version_compare(yml_data['toversion'], '5.0.0') < 0:
                    raise ValueError('Failed: {}. dockerimage45 set for 4.5 and earlier only'.format(self.dest_path))
                yml_text45 = re.sub(r'^toversion:.*$', 'toversion: 4.5.9', yml_text45, flags=re.MULTILINE)
            else:
                yml_text45 = 'toversion: 4.5.9\n' + yml_text45
            if script_obj.get('dockerimage45'):  # we have a value for dockerimage45 set it as dockerimage
                yml_text45 = re.sub(r'(^\s*dockerimage:).*$', r'\1 ' + script_obj.get('dockerimage45'),
                                    yml_text45, flags=re.MULTILINE)
            else:  # no value for dockerimage45 remove the dockerimage entry
                yml_text45 = re.sub(r'^\s*dockerimage:.*\n?', '', yml_text45, flags=re.MULTILINE)
            output_path45 = re.sub(r'\.yml$', '_45.yml', self.dest_path)
            output_map = {
                self.dest_path: yml_text,
                output_path45: yml_text45
            }
        for file_path, file_text in output_map.items():
            if os.path.isfile(file_path):
                raise ValueError('Output file already exists: {}.'
                                 ' Make sure to remove this file from source control'
                                 ' or rename this package (for example if it is a v2).'.format(self.dest_path))
            with io.open(file_path, mode='w', encoding='utf-8') as file_:
                file_.write(file_text)
        return output_map

    def merge_script_package_to_yml(self):
        """Merge the various components to create an output yml file

        Returns:
            output path, script path, image path
        """
        print("Merging package: {}".format(self.package_path))
        if self.package_path.endswith('/'):
            self.package_path = self.package_path.rstrip('/')
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}.yml'.format(DIR_TO_PREFIX[self.dir_name], package_dir_name)
        if self.dest_path:
            self.dest_path = os.path.join(self.dest_path, output_filename)
        else:
            self.dest_path = os.path.join(self.dir_name, output_filename)

        yml_paths, yml_path = get_yml_paths_in_dir(self.package_path, Errors.no_yml_file(self.package_path))
        for path in yml_paths:
            # The plugin creates a unified YML file for the package.
            # In case this script runs locally and there is a unified YML file in the package we need to ignore it.
            # Also,
            # we don't take the unified file by default because
            # there might be packages that were not created by the plugin.
            if 'unified' not in path:
                yml_path = path
                break

        with open(yml_path, 'r') as yml_file:
            yml_data = yaml.safe_load(yml_file)

        script_obj = yml_data

        if self.dir_name != SCRIPTS_DIR:
            script_obj = yml_data['script']
        script_type = TYPE_TO_EXTENSION[script_obj['type']]

        with io.open(yml_path, mode='r', encoding='utf-8') as yml_file:
            yml_text = yml_file.read()

        yml_text, script_path = self.insert_script_to_yml(script_type, yml_text, yml_data)
        image_path = None
        desc_path = None
        if self.dir_name in (INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR):
            yml_text, image_path = self.insert_image_to_yml(yml_data, yml_text)
            yml_text, desc_path = self.insert_description_to_yml(yml_data, yml_text)

        output_map = self.write_yaml_with_docker(yml_text, yml_data, script_obj)
        return list(output_map.keys()), yml_path, script_path, image_path, desc_path

    def insert_image_to_yml(self, yml_data, yml_text):
        image_data, found_img_path = self.get_data("*png")
        image_data = self.image_prefix + base64.b64encode(image_data).decode('utf-8')

        if yml_data.get('image'):
            yml_text = yml_text.replace(yml_data['image'], image_data)

        else:
            yml_text = 'image: ' + image_data + '\n' + yml_text
        # verify that our yml is good (loads and returns the image)
        mod_yml_data = yaml.safe_load(yml_text)
        yml_image = mod_yml_data.get('image')
        assert yml_image.strip() == image_data.strip()

        return yml_text, found_img_path

    def insert_description_to_yml(self, yml_data, yml_text):
        desc_data, found_desc_path = self.get_data('*_description.md')

        if yml_data.get('detaileddescription'):
            raise ValueError('Please move the detailed description from the yml to a description file (.md)'
                             ' in the package: {}'.format(self.package_path))
        if desc_data:
            desc_data = desc_data.decode('utf-8')
            if not desc_data.startswith('"'):
                # for multiline detailed-description, if it's not wrapped in quotation marks
                # add | to the beginning of the description, and shift everything to the right
                desc_data = '|\n  ' + desc_data.replace('\n', '\n  ')
            temp_yml_text = u"detaileddescription: "
            temp_yml_text += desc_data
            temp_yml_text += u"\n"
            temp_yml_text += yml_text

            yml_text = temp_yml_text

        return yml_text, found_desc_path

    def get_data(self, extension):
        data_path = glob.glob(os.path.join(self.package_path, extension))
        data = None
        found_data_path = None
        if self.dir_name in ('Integrations', 'Beta_Integrations') and data_path:
            found_data_path = data_path[0]
            with open(found_data_path, 'rb') as data_file:
                data = data_file.read()

        return data, found_data_path

    def get_code_file(self, script_type):
        """Return the first code file in the specified directory path
        :param script_type: script type: .py or .js
        :type script_type: str
        :return: path to found code file
        :rtype: str
        """

        ignore_regex = (r'CommonServerPython\.py|CommonServerUserPython\.py|demistomock\.py|_test\.py'
                        r'|conftest\.py|__init__\.py')
        if not self.package_path.endswith('/'):
            self.package_path += '/'
        if self.package_path.endswith('Scripts/CommonServerPython/'):
            return self.package_path + 'CommonServerPython.py'

        script_path = list(filter(lambda x: not re.search(ignore_regex, x),
                                  glob.glob(os.path.join(self.package_path, '*' + script_type))))[0]
        return script_path

    def insert_script_to_yml(self, script_type, yml_text, yml_data):
        script_path = self.get_code_file(script_type)
        with io.open(script_path, mode='r', encoding='utf-8') as script_file:
            script_code = script_file.read()

        clean_code = self.clean_python_code(script_code)

        lines = ['|-']
        lines.extend(u'    {}'.format(line) for line in clean_code.split('\n'))
        script_code = u'\n'.join(lines)

        if self.dir_name == 'Scripts':
            if yml_data.get('script'):
                if yml_data['script'] != '-' and yml_data['script'] != '':
                    raise ValueError("Please change the script to be blank or a dash(-) for package {}"
                                     .format(self.package_path))

        elif self.dir_name == 'Integrations' or self.dir_name == 'Beta_Integrations':
            if yml_data.get('script', {}).get('script'):
                if yml_data['script']['script'] != '-' and yml_data['script']['script'] != '':
                    raise ValueError("Please change the script to be blank or a dash(-) for package {}"
                                     .format(self.package_path))
        else:
            raise ValueError('Unknown yml type for dir: {}. Expecting: Scripts/Integrations'.format(self.package_path))

        yml_text = yml_text.replace("script: ''", "script: " + script_code)
        yml_text = yml_text.replace("script: '-'", "script: " + script_code)

        # verify that our yml is good (loads and returns the code)
        mod_yml_data = yaml.safe_load(yml_text)
        if self.dir_name == 'Scripts':
            yml_script = mod_yml_data.get('script')
        else:
            yml_script = mod_yml_data.get('script', {}).get('script')

        assert yml_script.strip() == clean_code.strip()

        return yml_text, script_path

    def get_script_package_data(self):
        _, yml_path = get_yml_paths_in_dir(self.package_path, error_msg='')
        if not yml_path:
            raise Exception("No yml files found in package path: {}. "
                            "Is this really a package dir? If not remove it.".format(self.package_path))
        code_type = get_yaml(yml_path).get('type')
        unifier = Unifier(self.package_path)
        code_path = unifier.get_code_file(TYPE_TO_EXTENSION[code_type])
        with open(code_path, 'r') as code_file:
            code = code_file.read()

        return yml_path, code

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
    def add_sub_parser(subparsers):
        parser = subparsers.add_parser('unify',
                                       help='Unify code, image and description files to a single Demisto yaml file')
        parser.add_argument("-i", "--indir", help="The path to the files to unify", required=True)
        parser.add_argument("-o", "--outdir", help="The output dir to write the unified yml to", required=True)
