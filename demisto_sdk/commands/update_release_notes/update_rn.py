"""
This script is used to create a release notes template
"""

import errno
import json
import os
import sys

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, IGNORED_PACK_NAMES,
    PACKS_PACK_META_FILE_NAME)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_json,
                                               get_latest_release_notes_text,
                                               pack_name_to_path, print_color,
                                               print_error, print_warning)


class UpdateRN:
    def __init__(self, pack: str, update_type: None, pack_files: set, added_files: set,
                 pre_release: bool = False):

        self.pack = pack
        self.update_type = update_type
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.pack_path = pack_name_to_path(self.pack)
        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')
        self.pack_files = pack_files
        self.added_files = added_files
        self.pre_release = pre_release

    def execute_update(self):
        if self.pack in IGNORED_PACK_NAMES:
            print_warning(f"Release notes are not required for the {self.pack} pack since this pack"
                          f" is not versioned.")
        else:
            try:
                new_version, new_metadata = self.bump_version_number(self.pre_release)
            except ValueError as e:
                print_error(e)
                sys.exit(1)
            rn_path = self.return_release_notes_path(new_version)
            self.check_rn_dir(rn_path)
            changed_files = {}
            self.find_added_pack_files()
            for packfile in self.pack_files:
                file_name, file_type = self.identify_changed_file_type(packfile)
                changed_files[file_name] = file_type
            rn_string = self.build_rn_template(changed_files)
            if len(rn_string) > 0:
                self.commit_to_bump(new_metadata)
                self.create_markdown(rn_path, rn_string, changed_files)
            else:
                print_warning("No changes which would belong in release notes were detected.")

    def _does_pack_metadata_exist(self):
        """Check if pack_metadata.json exists"""
        if not os.path.isfile(self.metadata_path):
            print_error(f'"{self.metadata_path}" file does not exist, create one in the root of the pack')
            return False

        return True

    def find_added_pack_files(self):
        for a_file in self.added_files:
            if self.pack in a_file:
                if any(item in a_file for item in ALL_FILES_VALIDATION_IGNORE_WHITELIST):
                    continue
                else:
                    self.pack_files.add(a_file)

    def return_release_notes_path(self, input_version: str):
        _new_version = input_version.replace('.', '_')
        new_version = _new_version.replace('_prerelease', '')
        return os.path.join(self.pack_path, 'ReleaseNotes', f'{new_version}.md')

    @staticmethod
    def get_display_name(file_path):
        struct = StructureValidator(file_path=file_path, is_new_file=True)
        file_data = struct.load_data_from_file()
        if 'name' in file_data:
            name = file_data.get('name', None)
        elif 'TypeName' in file_data:
            name = file_data.get('TypeName', None)
        elif 'brandName' in file_data:
            name = file_data.get('brandName', None)
        else:
            name = os.path.basename(file_path)
        return name

    @staticmethod
    def find_corresponding_yml(file_path):
        if file_path.endswith('.py'):
            yml_filepath = file_path.replace('.py', '.yml')
        else:
            yml_filepath = file_path
        return yml_filepath

    def identify_changed_file_type(self, file_path):
        _file_type = None
        file_name = 'N/A'
        if 'ReleaseNotes' in file_path:
            return file_name, _file_type
        if self.pack in file_path and ('README' not in file_path):
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
        try:
            data_dictionary = get_json(self.metadata_path)
        except FileNotFoundError:
            print_error(f"Pack {self.pack} was not found. Please verify the pack name is correct.")
            sys.exit(1)
        if self.update_type is None:
            new_version = data_dictionary.get('currentVersion', '99.99.99')
            return new_version, data_dictionary
        elif self.update_type == 'major':
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
        return new_version, data_dictionary

    def commit_to_bump(self, metadata_dict):
        if self._does_pack_metadata_exist():
            with open(self.metadata_path, 'w') as file_path:
                json.dump(metadata_dict, file_path, indent=4)
                print_color(f"Updated pack metadata version at path : {self.metadata_path}",
                            LOG_COLORS.GREEN)

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
                if not integration_header:
                    rn_string += '\n### Integrations\n'
                    integration_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Playbook':
                if not playbook_header:
                    rn_string += '\n### Playbooks\n'
                    playbook_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Script':
                if not script_header:
                    rn_string += '\n### Scripts\n'
                    script_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'IncidentFields':
                if not inc_flds_header:
                    rn_string += '\n### IncidentFields\n'
                    inc_flds_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Classifiers':
                if not classifier_header:
                    rn_string += '\n### Classifiers\n'
                    classifier_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'Layouts':
                if not layout_header:
                    rn_string += '\n### Layouts\n'
                    layout_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
            elif v == 'IncidentTypes':
                if not inc_types_header:
                    rn_string += '\n### IncidentTypes\n'
                    inc_types_header = True
                rn_string += f'- __{k}__\n%%UPDATE_RN%%\n'
        return rn_string

    @staticmethod
    def update_existing_rn(current_rn, changed_files):
        new_rn = current_rn
        for k, v in sorted(changed_files.items(), reverse=True):
            if v is None:
                continue
            if v in current_rn:
                v = v[:-1] if v.endswith('s') else v
                if k in current_rn:
                    continue
                else:
                    rn_parts = new_rn.split(v + 's')
                    new_rn_part = f'\n- __{k}__\n%%UPDATE_RN%%\n'
                    if len(rn_parts) > 1:
                        new_rn = rn_parts[0] + v + 's' + new_rn_part + rn_parts[1]
                    else:
                        new_rn = ''.join(rn_parts) + new_rn_part
            else:
                if v in new_rn:
                    rn_parts = new_rn.split(v + 's')
                    new_rn_part = f'\n- __{k}__\n%%UPDATE_RN%%\n'
                    if len(rn_parts) > 1:
                        new_rn = rn_parts[0] + v + 's' + new_rn_part + rn_parts[1]
                    else:
                        new_rn = ''.join(rn_parts) + new_rn_part
                else:
                    new_rn_part = f'\n### {v}\n- __{k}__\n%%UPDATE_RN%%\n'
                    new_rn += new_rn_part
        return new_rn

    def create_markdown(self, release_notes_path: str, rn_string: str, changed_files: dict):
        if os.path.exists(release_notes_path) and self.update_type is not None:
            print_warning(f"Release notes were found at {release_notes_path}. Skipping")
        elif self.update_type is None:
            current_rn = get_latest_release_notes_text(release_notes_path)
            updated_rn = self.update_existing_rn(current_rn, changed_files)
            with open(release_notes_path, 'w') as fp:
                fp.write(updated_rn)
        else:
            with open(release_notes_path, 'w') as fp:
                fp.write(rn_string)
