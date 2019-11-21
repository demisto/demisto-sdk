import os
import io
import glob
import yaml
import base64
import re

from ..common.tools import get_yaml
from ..common.constants import TYPE_TO_EXTENSION, INTEGRATIONS_DIR, INTEGRATION_PREFIX


class Unifier:

    def __init__(self, package_path: str, dir_name=INTEGRATIONS_DIR, dest_path='',
                 integration_prefix=INTEGRATION_PREFIX, script_prefix='script', image_prefix='data:image/png;base64,'):

        self.dir_to_prefix = {
            'Integrations': integration_prefix,
            'Beta_Integrations': integration_prefix,
            'Scripts': script_prefix
        }

        self.type_to_ext = {
            'python': '.py',
            'javascript': '.js'
        }

        self.image_prefix = image_prefix
        self.package_path = package_path
        if not self.package_path.endswith('/'):
            self.package_path += '/'

        self.dir_name = dir_name
        self.dest_path = dest_path

    def merge_script_package_to_yml(self):
        """Merge the various components to create an output yml file

        Args:

        Returns:
            output path, script path, image path
        """
        print("Merging package: {}".format(self.package_path))
        output_filename = '{}-{}.yml'.format(self.dir_to_prefix[self.dir_name],
                                             os.path.basename(os.path.dirname(self.package_path)))
        if self.dest_path:
            output_path = os.path.join(self.dest_path, output_filename)
        else:
            output_path = os.path.join(self.dir_name, output_filename)

        yml_paths = glob.glob(self.package_path + '*.yml')
        yml_path = yml_paths[0]
        for path in yml_paths:
            # The plugin creates a unified YML file for the package.
            # In case this script runs locally and there is a unified YML file in the package we need to ignore it.
            # Also,
            # we don't take the unified file by default because there might be packages
            # that were not created by the plugin.
            if 'unified' not in path:
                yml_path = path
                break

        with open(yml_path, 'r') as yml_file:
            yml_data = yaml.safe_load(yml_file)

        if self.dir_name == 'Scripts':
            script_type = self.type_to_ext[yml_data['type']]
        elif self.dir_name == 'Integrations' or 'Beta_Integrations':
            script_type = self.type_to_ext[yml_data['script']['type']]

        with io.open(yml_path, mode='r', encoding='utf-8') as yml_file:
            yml_text = yml_file.read()

        yml_text, script_path = self.insert_script_to_yml(script_type, yml_text, yml_data)
        image_path = None
        desc_path = None
        if self.dir_name == 'Integrations' or self.dir_name == 'Beta_Integrations':
            yml_text, image_path = self.insert_image_to_yml(yml_data, yml_text)
            yml_text, desc_path = self.insert_description_to_yml(yml_data, yml_text)

        with io.open(output_path, mode='w', encoding='utf-8') as f:
            f.write(yml_text)
        return output_path, yml_path, script_path, image_path, desc_path

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
        data_path = glob.glob(self.package_path + extension)
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

        ignore_regex = (r'CommonServerPython\.py|CommonServerUserPython\.py|demistomock\.py|test_.*\.py|_test\.py'
                        r'|conftest\.py')
        if not self.package_path.endswith('/'):
            self.package_path += '/'
        if self.package_path.endswith('Scripts/CommonServerPython/'):
            return self.package_path + 'CommonServerPython.py'

        script_path = list(filter(lambda x: not re.search(ignore_regex, x),
                                  glob.glob(self.package_path + '*' + script_type)))[0]
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
        if self.package_path[-1] != os.sep:
            package_path = os.path.join(self.package_path, '')
        yml_files = glob.glob(package_path + '*.yml')
        if not yml_files:
            raise Exception("No yml files found in package path: {}. "
                            "Is this really a package dir? If not remove it.".format(package_path))
        yml_path = yml_files[0]
        code_type = get_yaml(yml_path).get('type')
        unifier = Unifier(package_path)
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
