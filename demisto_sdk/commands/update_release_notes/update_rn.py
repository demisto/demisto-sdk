"""
This script is used to create a release notes template
"""

import errno
import json
import os
import sys

from demisto_sdk.commands.common.constants import PACKS_PACK_META_FILE_NAME
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_json,
                                               pack_name_to_path, print_color,
                                               print_error, print_warning)


class UpdateRN:
    def __init__(self, pack: str, update_type: str, pack_files: set, pre_release: bool = False):

        self.pack = pack
        self.update_type = update_type
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.pack_path = pack_name_to_path(self.pack)
        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')
        self.pack_files = pack_files
        self.pre_release = pre_release

    def execute_update(self):
        try:
            new_version = self.bump_version_number(self.pre_release)
        except ValueError as e:
            print_error(e)
            sys.exit(1)
        rn_path = self.return_release_notes_path(new_version)
        self.check_rn_dir(rn_path)
        changed_files = {}
        for packfile in self.pack_files:
            fn, ft = self.ident_changed_file_type(packfile)
            changed_files[fn] = ft
        rn_string = self.build_rn_template(changed_files)
        self.create_markdown(rn_path, rn_string)

    def _does_pack_metadata_exist(self):
        """Check if pack_metadata.json exists"""
        if not os.path.isfile(self.metadata_path):
            print_error(f'"{self.metadata_path}" file does not exist, create one in the root of the pack')
            return False

        return True

    def return_release_notes_path(self, input_version: str):
        _new_version = input_version.replace('.', '_')
        new_version = _new_version.replace('_prerelease', '')
        return os.path.join(self.pack_path, 'ReleaseNotes', f'{new_version}.md')

    @staticmethod
    def get_display_name(file_path):
        struct = StructureValidator(file_path=file_path)
        file_data = struct.load_data_from_file()
        if 'name' in file_data:
            name = file_data.get('name', None)
        elif 'TypeName' in file_data:
            name = file_data.get('TypeName', None)
        else:
            name = os.path.basename(file_path)
            print_error(f"Could not find name in {file_path}")
            # sys.exit(1)
        return name

    @staticmethod
    def find_corresponding_yml(file_path):
        if file_path.endswith('.py'):
            yml_filepath = file_path.replace('.py', '.yml')
        else:
            yml_filepath = file_path
        return yml_filepath

    def ident_changed_file_type(self, file_path):
        _file_type = None
        file_name = 'N/A'
        if self.pack in file_path:
            _file_path = self.find_corresponding_yml(file_path)
            file_name = self.get_display_name(_file_path)
            if 'Playbooks' in file_path and ('TestPlaybooks' not in file_path):
                _file_type = 'Playbook'
            elif 'Integration' in file_path:
                _file_type = 'Integration'
            elif 'Script' in file_path:
                _file_type = 'Script'
            # incident fields and indicator fields are using the same scheme.
            elif 'IncidentFields' in file_path:
                _file_type = 'IncidentFields'
            elif 'IncidentTypes' in file_path:
                _file_type = 'IncidentTypes'
            elif 'Classifiers' in file_path:
                _file_type = 'Classifiers'
            elif 'Layouts' in file_path:
                _file_type = 'Layout'

        return file_name, _file_type

    def bump_version_number(self, pre_release: bool = False):

        new_version = None  # This will never happen since we pre-validate the argument
        data_dictionary = get_json(self.metadata_path)
        if self.update_type == 'major':
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[0] = str(int(version[0]) + 1)
            if int(version[0]) > 99:
                raise ValueError(f"Version number is greater than 99 for the {self.pack} pack. "
                                 f"Please verify the currentVersion is correct.")
            version[1] = '0'
            version[2] = '0'
            new_version = '.'.join(version)
        elif self.update_type == 'minor':
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[1] = str(int(version[1]) + 1)
            if int(version[1]) > 99:
                raise ValueError(f"Version number is greater than 99 for the {self.pack} pack. "
                                 f"Please verify the currentVersion is correct. If it is, "
                                 f"then consider bumping to a new Major version.")
            version[2] = '0'
            new_version = '.'.join(version)
        # We validate the input via click
        elif self.update_type == 'revision':
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[2] = str(int(version[2]) + 1)
            if int(version[2]) > 99:
                raise ValueError(f"Version number is greater than 99 for the {self.pack} pack. "
                                 f"Please verify the currentVersion is correct. If it is, "
                                 f"then consider bumping to a new Minor version.")
            new_version = '.'.join(version)
        if pre_release:
            new_version = new_version + '_prerelease'
        data_dictionary['currentVersion'] = new_version

        if self._does_pack_metadata_exist():
            with open(self.metadata_path, 'w') as fp:
                json.dump(data_dictionary, fp, indent=4)
                print_color(f"Updated pack metadata version at path : {self.metadata_path}",
                            LOG_COLORS.GREEN)
        return new_version

    @staticmethod
    def check_rn_dir(rn_path):
        if not os.path.exists(os.path.dirname(rn_path)):
            try:
                os.makedirs(os.path.dirname(rn_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def build_rn_template(self, changed_items: dict):
        rn_string = ''
        integration_header = False
        playbook_header = False
        script_header = False
        inc_flds_header = False
        classifier_header = False
        layout_header = False
        inc_types_header = False
        for k, v in changed_items.items():
            if k == 'N/A':
                continue
            elif v == 'Integration':
                if integration_header is False:
                    rn_string += '\n#### Integrations\n'
                    integration_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Playbook':
                if playbook_header is False:
                    rn_string += '\n#### Playbooks\n'
                    playbook_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Script':
                if script_header is False:
                    rn_string += '\n#### Scripts\n'
                    script_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'IncidentFields':
                if inc_flds_header is False:
                    rn_string += '\n#### IncidentFields\n'
                    inc_flds_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Classifiers':
                if classifier_header is False:
                    rn_string += '\n#### Classifiers\n'
                    classifier_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Layouts':
                if layout_header is False:
                    rn_string += '\n#### Layouts\n'
                    layout_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'IncidentTypes':
                if inc_types_header is False:
                    rn_string += '\n#### IncidentTypes\n'
                    inc_types_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
        return rn_string

    @staticmethod
    def create_markdown(release_notes_path: str, rn_string: str):
        if os.path.exists(release_notes_path):
            print_warning(f"Release notes were found at {release_notes_path}. Skipping")
        else:
            with open(release_notes_path, 'w') as fp:
                fp.write(rn_string)
