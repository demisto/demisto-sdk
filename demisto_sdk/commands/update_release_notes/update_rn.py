"""
This script is used to create a release notes template
"""

import errno
import json
import os
import sys
from typing import Union

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, IGNORED_PACK_NAMES,
    PACKS_PACK_META_FILE_NAME)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_json,
                                               get_latest_release_notes_text,
                                               get_pack_name, get_yaml,
                                               pack_name_to_path, print_color,
                                               print_error, print_warning,
                                               run_command)


class UpdateRN:
    def __init__(self, pack_path: str, update_type: Union[str, None], pack_files: set, added_files: set,
                 specific_version: str = None, pre_release: bool = False, pack: str = None,
                 pack_metadata_only: bool = False):
        self.pack = pack if pack else get_pack_name(pack_path)
        self.update_type = update_type
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.pack_path = pack_name_to_path(self.pack)
        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')
        self.pack_files = pack_files
        self.added_files = added_files
        self.pre_release = pre_release
        self.specific_version = specific_version
        self.existing_rn_changed = False
        self.pack_metadata_only = pack_metadata_only

    def execute_update(self):
        if self.pack in IGNORED_PACK_NAMES:
            print_warning(f"Release notes are not required for the {self.pack} pack since this pack"
                          f" is not versioned.")
        else:
            try:
                if self.is_bump_required():
                    if self.update_type is None:
                        self.update_type = "revision"
                    new_version, new_metadata = self.bump_version_number(self.specific_version, self.pre_release)
                    print_color(f"Changes were detected. Bumping {self.pack} to version: {new_version}",
                                LOG_COLORS.NATIVE)
                else:
                    new_metadata = self.get_pack_metadata()
                    new_version = new_metadata.get('currentVersion', '99.99.99')
            except ValueError as e:
                print_error(e)
                sys.exit(1)
            rn_path = self.return_release_notes_path(new_version)
            self.check_rn_dir(rn_path)
            changed_files = {}
            self.find_added_pack_files()
            for packfile in self.pack_files:
                file_name, file_type = self.identify_changed_file_type(packfile)

                changed_files[file_name] = {
                    'type': file_type,
                    'description': get_file_description(packfile, file_type),
                    'is_new_file': True if packfile in self.added_files else False
                }

            rn_string = self.build_rn_template(changed_files)
            if len(rn_string) > 0:
                if self.is_bump_required():
                    self.commit_to_bump(new_metadata)
                self.create_markdown(rn_path, rn_string, changed_files)
                if self.existing_rn_changed:
                    print_color(f"Finished updating release notes for {self.pack}."
                                f"\nNext Steps:\n - Please review the "
                                f"created release notes found at {rn_path} and document any changes you "
                                f"made by replacing '%%UPDATE_RN%%'.\n - Commit "
                                f"the new release notes to your branch.\nFor information regarding proper"
                                f" format of the release notes, please refer to "
                                f"https://xsoar.pan.dev/docs/integrations/changelog", LOG_COLORS.GREEN)
                else:
                    print_color("No changes to pack files were detected from the previous time "
                                "this command was run. The release notes have not been "
                                "changed.", LOG_COLORS.GREEN)
            else:
                print_warning("No changes which would belong in release notes were detected.")

    def _does_pack_metadata_exist(self):
        """Check if pack_metadata.json exists"""
        if not os.path.isfile(self.metadata_path):
            print_error(f'"{self.metadata_path}" file does not exist, create one in the root of the pack')
            return False

        return True

    def is_bump_required(self):
        try:
            diff = run_command(f"git diff master:{self.metadata_path} {self.metadata_path}")
            if '+    "currentVersion"' in diff:
                return False
            if self.only_readme_changed():
                return False
        except RuntimeError:
            print_warning(f"Unable to locate a pack with the name {self.pack} in the git diff. "
                          f"Please verify the pack exists and the pack name is correct.")
        return True

    def only_readme_changed(self):
        changed_files = self.added_files.union(self.pack_files)
        if len(changed_files) == 1 and 'README' in changed_files.pop():
            return True
        return False

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
        if 'display' in file_data:
            name = file_data.get('display', None)
        elif 'name' in file_data:
            name = file_data.get('name', None)
        elif 'TypeName' in file_data:
            name = file_data.get('TypeName', None)
        elif 'brandName' in file_data:
            name = file_data.get('brandName', None)
        elif 'id' in file_data:
            name = file_data.get('id', None)
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
        if 'ReleaseNotes' in file_path or 'TestPlaybooks' in file_path:
            return file_name, _file_type

        if self.pack in file_path and ('README' not in file_path):
            _file_path = self.find_corresponding_yml(file_path)
            file_name = self.get_display_name(_file_path)
            file_path = file_path.replace(self.pack_path, '')

            if 'Playbooks' in file_path:
                _file_type = 'Playbook'
            elif 'Integrations' in file_path:
                _file_type = 'Integration'
            elif 'Scripts' in file_path:
                _file_type = 'Script'
            # incident fields and indicator fields are using the same scheme.
            elif 'IncidentFields' in file_path:
                _file_type = 'Incident Fields'
            elif 'IndicatorTypes' in file_path:
                _file_type = 'Indicator Types'
            elif 'IncidentTypes' in file_path:
                _file_type = 'Incident Types'
            elif 'Classifiers' in file_path:
                _file_type = 'Classifiers'
            elif 'Layouts' in file_path:
                _file_type = 'Layouts'
            elif 'Reports' in file_path:
                _file_type = 'Reports'
            elif 'Widgets' in file_path:
                _file_type = 'Widgets'
            elif 'Dashboards' in file_path:
                _file_type = 'Dashboards'
            elif 'Connections' in file_path:
                _file_type = 'Connections'

        return file_name, _file_type

    def get_pack_metadata(self):
        try:
            data_dictionary = get_json(self.metadata_path)
        except FileNotFoundError:
            print_error(f"Pack {self.pack} was not found. Please verify the pack name is correct.")
            sys.exit(1)
        return data_dictionary

    def bump_version_number(self, specific_version: str = None, pre_release: bool = False):
        if self.update_type is None and specific_version is None:
            raise ValueError("Received no update type when one was expected.")
        new_version = ''  # This will never happen since we pre-validate the argument
        data_dictionary = self.get_pack_metadata()
        if specific_version:
            print_color(f"Bumping {self.pack} to the version {specific_version}. If you need to update"
                        f" the release notes a second time, please remove the -v flag.", LOG_COLORS.NATIVE)
            data_dictionary['currentVersion'] = specific_version
            return specific_version, data_dictionary
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
        ind_types_header = False
        rep_types_header = False
        widgets_header = False
        dashboards_header = False
        connections_header = False
        if self.pack_metadata_only:
            rn_string += f'\n#### Integrations\n##### {self.pack}\n- Documentation and metadata improvements.\n'
            return rn_string

        for content_name, data in sorted(changed_items.items(),
                                         key=lambda x: x[1].get('type', '') if x[1].get('type') is not None else ''):
            desc = data.get('description', '')
            is_new_file = data.get('is_new_file', False)
            _type = data.get('type', '')

            # Skipping the invalid files
            if not _type or content_name == 'N/A':
                continue

            if _type in ('Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'):
                rn_desc = f'- **{content_name}**\n'
            else:
                rn_desc = f'##### New: {content_name}\n- {desc}\n' if is_new_file \
                    else f'##### {content_name}\n- %%UPDATE_RN%%\n'

            if _type == 'Integration':
                if not integration_header:
                    rn_string += '\n#### Integrations\n'
                    integration_header = True
                rn_string += rn_desc
            elif _type == 'Playbook':
                if not playbook_header:
                    rn_string += '\n#### Playbooks\n'
                    playbook_header = True
                rn_string += rn_desc
            elif _type == 'Script':
                if not script_header:
                    rn_string += '\n#### Scripts\n'
                    script_header = True
                rn_string += rn_desc
            elif _type == 'Incident Fields':
                if not inc_flds_header:
                    rn_string += '\n#### Incident Fields\n'
                    inc_flds_header = True
                rn_string += rn_desc
            elif _type == 'Classifiers':
                if not classifier_header:
                    rn_string += '\n#### Classifiers\n'
                    classifier_header = True
                rn_string += rn_desc
            elif _type == 'Layouts':
                if not layout_header:
                    rn_string += '\n#### Layouts\n'
                    layout_header = True
                rn_string += rn_desc
            elif _type == 'Incident Types':
                if not inc_types_header:
                    rn_string += '\n#### Incident Types\n'
                    inc_types_header = True
                rn_string += rn_desc
            elif _type == 'Indicator Types':
                if not ind_types_header:
                    rn_string += '\n#### Indicator Types\n'
                    ind_types_header = True
                rn_string += rn_desc
            elif _type == 'Reports':
                if not rep_types_header:
                    rn_string += '\n#### Reports\n'
                    rep_types_header = True
                rn_string += rn_desc
            elif _type == 'Widgets':
                if not widgets_header:
                    rn_string += '\n#### Widgets\n'
                    widgets_header = True
                rn_string += rn_desc
            elif _type == 'Dashboards':
                if not dashboards_header:
                    rn_string += '\n#### Dashboards\n'
                    dashboards_header = True
                rn_string += rn_desc
            elif _type == 'Connections':
                if not connections_header:
                    rn_string += '\n#### Connections\n'
                    connections_header = True
                rn_string += rn_desc
        return rn_string

    def update_existing_rn(self, current_rn, changed_files):
        new_rn = current_rn
        for content_name, data in sorted(changed_files.items(), reverse=True):
            is_new_file = data.get('is_new_file')
            desc = data.get('description', '')
            _type = data.get('type', '')

            if _type is None:
                continue

            if _type in ('Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'):
                rn_desc = f'\n- **{content_name}**'
            else:
                rn_desc = f'\n##### New: {content_name}\n- {desc}\n' if is_new_file\
                    else f'\n##### {content_name}\n- %%UPDATE_RN%%\n'

            if _type in current_rn:
                _type = _type[:-1] if _type.endswith('s') else _type
                if content_name in current_rn:
                    continue
                else:
                    self.existing_rn_changed = True
                    rn_parts = new_rn.split(_type + 's')
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = rn_parts[0] + _type + 's' + new_rn_part + rn_parts[1]
                    else:
                        new_rn = ''.join(rn_parts) + new_rn_part
            else:
                self.existing_rn_changed = True
                if _type in new_rn:
                    rn_parts = new_rn.split(_type + 's')
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = rn_parts[0] + _type + 's' + new_rn_part + rn_parts[1]
                    else:
                        new_rn = ''.join(rn_parts) + new_rn_part
                else:
                    new_rn_part = f'\n#### {_type}{rn_desc}'
                    new_rn += new_rn_part
        return new_rn

    def create_markdown(self, release_notes_path: str, rn_string: str, changed_files: dict):
        if os.path.exists(release_notes_path) and self.update_type is not None:
            print_warning(f"Release notes were found at {release_notes_path}. Skipping")
        elif self.update_type is None and self.specific_version is None:
            current_rn = get_latest_release_notes_text(release_notes_path)
            updated_rn = self.update_existing_rn(current_rn, changed_files)
            with open(release_notes_path, 'w') as fp:
                fp.write(updated_rn)
        else:
            self.existing_rn_changed = True
            with open(release_notes_path, 'w') as fp:
                fp.write(rn_string)


def get_file_description(path, file_type):
    if not os.path.isfile(path):
        print_warning(f'Cannot get file description: "{path}" file does not exist')
        return ''

    elif file_type in ('Playbook', 'Integration'):
        yml_file = get_yaml(path)
        return yml_file.get('description', '')

    elif file_type == 'Script':
        yml_file = get_yaml(path)
        return yml_file.get('comment', '')

    elif file_type in ('Classifiers', 'Reports', 'Widgets', 'Dashboards'):
        json_file = get_json(path)
        return json_file.get('description', '')

    return '%%UPDATE_RN%%'
