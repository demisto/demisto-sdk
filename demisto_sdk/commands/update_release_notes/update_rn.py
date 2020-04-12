"""
This script is used to create a release notes template
"""

import errno
import json
import os

from demisto_sdk.commands.common.constants import PACKS_PACK_META_FILE_NAME
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_json,
                                               pack_name_to_path, print_color,
                                               print_error)
from demisto_sdk.commands.validate.file_validator import FilesValidator


class UpdateRN:
    def __init__(self, pack: str, update_type: str):

        self.pack = pack
        self.update_type = update_type
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.pack_path = pack_name_to_path(self.pack)
        # if self._does_pack_metadata_exist(self.pack_meta_file):
        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')

    @staticmethod
    def get_master_diff():
        a, b, c, packs = FilesValidator(use_git=True).get_modified_and_added_files()

        return a

    def _does_pack_metadata_exist(self):
        """Check if pack_metadata.json exists"""
        if not os.path.isfile(self.metadata_path):
            print_error('"{}" file does not exist, create one in the root of the pack'.format(
                self.metadata_path))
            return False

        return True

    def return_release_notes_path(self, input_version: str):
        new_version = input_version.replace('.', '_')
        return os.path.join(self.pack_path, 'ReleaseNotes', '{}.md'.format(new_version))

    @staticmethod
    def format_filename(file_path):
        raw_name = os.path.basename(file_path)
        _raw_name = str(raw_name).split('.')
        file_name = _raw_name[0].replace('_', ' ')
        return file_name

    def ident_changed_file_type(self, file_path):
        _file_type = None
        file_name = 'N/A'
        if self.pack in file_path:
            _file_name = os.path.basename(file_path)
            file_name = self.format_filename(_file_name)
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

    def bump_version_number(self):
        data_dictionary = get_json(self.metadata_path)
        if self.update_type == 'major':
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[0] = str(int(version[0]) + 1)
            new_version = '.'.join(version)
        elif self.update_type == 'minor':
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[1] = str(int(version[1]) + 1)
            new_version = '.'.join(version)
        # We validate the input via click
        else:
            version = data_dictionary.get('currentVersion', '99.99.99')
            version = version.split('.')
            version[2] = str(int(version[2]) + 1)
            new_version = '.'.join(version)
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
        rn_string = f'''<details>\n<summary>{self.pack}</summary>\n'''
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
        rn_string += '</details>'
        return rn_string

    @staticmethod
    def create_markdown(release_notes_path: str, rn_string: str):
        with open(release_notes_path, 'w') as fp:
            fp.write(rn_string)
