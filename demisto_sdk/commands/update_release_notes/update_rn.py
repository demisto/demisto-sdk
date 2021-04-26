"""
This script is used to create a release notes template
"""
import copy
import errno
import json
import os
import re
import sys
from distutils.version import LooseVersion
from typing import Optional, Union

import click
from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, DEFAULT_ID_SET_PATH,
    IGNORED_PACK_NAMES, PACKS_PACK_META_FILE_NAME, RN_HEADER_BY_FILE_TYPE,
    FileType)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               get_api_module_ids,
                                               get_api_module_integrations_set,
                                               get_from_version, get_json,
                                               get_latest_release_notes_text,
                                               get_pack_name, get_remote_file,
                                               get_yaml, pack_name_to_path,
                                               print_color, print_error,
                                               print_warning, run_command)


class UpdateRN:
    def __init__(self, pack_path: str, update_type: Union[str, None], modified_files_in_pack: set, added_files: set,
                 specific_version: str = None, pre_release: bool = False, pack: str = None,
                 pack_metadata_only: bool = False, text: str = '', existing_rn_version_path: str = ''):
        self.pack = pack if pack else get_pack_name(pack_path)
        self.update_type = update_type
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        try:
            self.pack_path = pack_name_to_path(self.pack)
        except TypeError:
            click.secho(f'Please verify the pack path is correct: {self.pack}.', fg='red')
            sys.exit(1)
        # renamed files will appear in the modified list as a tuple: (old path, new path)
        modified_files_in_pack = {file_[1] if isinstance(file_, tuple) else file_ for file_ in modified_files_in_pack}
        self.modified_files_in_pack = set()
        for file_path in modified_files_in_pack:
            self.modified_files_in_pack.add(self.check_for_release_notes_valid_file_path(file_path))

        self.added_files = added_files
        self.pre_release = pre_release
        self.specific_version = specific_version
        self.existing_rn_changed = False
        self.text = text
        self.existing_rn_version_path = existing_rn_version_path
        self.should_delete_existing_rn = False
        self.pack_metadata_only = pack_metadata_only

        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')
        self.master_version = self.get_master_version()

    @staticmethod
    def check_for_release_notes_valid_file_path(file_path):
        """A method to change image and description file paths to the corresponding yml file path
        if a non-image or description file path is given, it remains unchanged
        """
        if file_path.endswith('_image.png'):
            return file_path.replace('_image.png', '.yml')

        elif file_path.endswith('_description.md'):
            return file_path.replace('_description.md', '.yml')

        return file_path

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
                click.secho(str(e), fg='red')
                sys.exit(1)
            rn_path = self.return_release_notes_path(new_version)
            self.check_rn_dir(rn_path)
            changed_files = {}
            self.find_added_pack_files()
            docker_image_name: Optional[str] = None
            for packfile in self.modified_files_in_pack:
                file_name, file_type = self.identify_changed_file_type(packfile)
                if 'yml' in packfile and file_type == FileType.INTEGRATION and packfile not in self.added_files:
                    docker_image_name = check_docker_image_changed(packfile)
                changed_files[file_name] = {
                    'type': file_type,
                    'description': get_file_description(packfile, file_type),
                    'is_new_file': True if packfile in self.added_files else False,
                    'fromversion': get_from_version_at_update_rn(packfile)
                }

            rn_string = ''
            if self.existing_rn_version_path:
                self.should_delete_existing_rn = False if self.existing_rn_version_path == rn_path else True
                try:
                    with open(self.existing_rn_version_path, 'r') as f:
                        rn_string = f.read()
                except Exception as e:
                    print_error(f'Failed to load the previous release notes file content: {e}')

            if not rn_string:
                rn_string = self.build_rn_template(changed_files)
            if len(rn_string) > 0:
                if self.is_bump_required():
                    self.commit_to_bump(new_metadata)
                self.create_markdown(rn_path, rn_string, changed_files, docker_image_name)
                if self.existing_rn_changed:
                    print_color(f"Finished updating release notes for {self.pack}."
                                f"\nNext Steps:\n - Please review the "
                                f"created release notes found at {rn_path} and document any changes you "
                                f"made by replacing '%%UPDATE_RN%%'.\n - Commit "
                                f"the new release notes to your branch.\nFor information regarding proper"
                                f" format of the release notes, please refer to "
                                f"https://xsoar.pan.dev/docs/integrations/changelog", LOG_COLORS.GREEN)
                    return True
                else:
                    click.secho("No changes to pack files were detected from the previous time "
                                "this command was run. The release notes have not been "
                                "changed.", fg='green')
            else:
                click.secho("No changes which would belong in release notes were detected.", fg='yellow')
        return False

    def _does_pack_metadata_exist(self):
        """Check if pack_metadata.json exists"""
        if not os.path.isfile(self.metadata_path):
            print_error(f'"{self.metadata_path}" file does not exist, create one in the root of the pack')
            return False

        return True

    def get_master_version(self):
        """
        Get the current version from origin/master if available, otherwise return '0.0.0'
        """
        master_current_version = '0.0.0'
        master_metadata = None
        try:
            master_metadata = get_remote_file(self.metadata_path)
        except Exception as e:
            print_error(f"master branch is unreachable.\n The reason is:{e} \n "
                        f"The updated version will be taken from local metadata file instead of master")
        if master_metadata:
            master_current_version = master_metadata.get('currentVersion', '0.0.0')
        return master_current_version

    def is_bump_required(self):
        """
        This function checks to see if the currentVersion in the pack metadata has been changed or
        not. Additionally, it will verify that there is no conflict with the currentVersion in the
        Master branch.
        """
        try:
            if self.only_docs_changed():
                return False
            new_metadata = self.get_pack_metadata()
            new_version = new_metadata.get('currentVersion', '99.99.99')
            if LooseVersion(self.master_version) >= LooseVersion(new_version):
                return True
            return False
        except RuntimeError:
            print_error(f"Unable to locate a pack with the name {self.pack} in the git diff.\n"
                        f"Please verify the pack exists and the pack name is correct.")
            sys.exit(0)

    def only_docs_changed(self):
        changed_files = self.added_files.union(self.modified_files_in_pack)
        changed_files_copy = copy.deepcopy(changed_files)  # copying as pop will leave the file out of the set
        if (len(changed_files) == 1 and 'README' in changed_files_copy.pop()) or \
                (all('README' in file or ('.png' in file and '_image.png' not in file) for file in changed_files)):
            return True
        return False

    def find_added_pack_files(self):
        """Check for added files in the given pack that require RN"""
        for a_file in self.added_files:
            if self.pack in a_file:
                if any(item in a_file for item in ALL_FILES_VALIDATION_IGNORE_WHITELIST):
                    continue
                else:
                    self.modified_files_in_pack.add(self.check_for_release_notes_valid_file_path(a_file))

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

        if self.pack + '/' in file_path and ('README' not in file_path):
            _file_path = self.find_corresponding_yml(file_path)
            file_name = self.get_display_name(_file_path)
            _file_type = find_type(_file_path)

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
        current_version = self.master_version if self.master_version != '0.0.0' else self.get_pack_metadata().get(
            'currentVersion', '99.99.99')
        if specific_version:
            print_color(f"Bumping {self.pack} to the version {specific_version}. If you need to update"
                        f" the release notes a second time, please remove the -v flag.", LOG_COLORS.NATIVE)
            data_dictionary['currentVersion'] = specific_version
            return specific_version, data_dictionary
        elif self.update_type == 'major':
            version = current_version.split('.')
            version[0] = str(int(version[0]) + 1)
            if int(version[0]) > 99:
                raise ValueError(f"Version number is greater than 99 for the {self.pack} pack. "
                                 f"Please verify the currentVersion is correct.")
            version[1] = '0'
            version[2] = '0'
            new_version = '.'.join(version)
        elif self.update_type == 'minor':
            version = current_version.split('.')
            version[1] = str(int(version[1]) + 1)
            if int(version[1]) > 99:
                raise ValueError(f"Version number is greater than 99 for the {self.pack} pack. "
                                 f"Please verify the currentVersion is correct. If it is, "
                                 f"then consider bumping to a new Major version.")
            version[2] = '0'
            new_version = '.'.join(version)
        # We validate the input via click
        elif self.update_type in ['revision', 'maintenance', 'documentation']:
            version = current_version.split('.')
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

        if self.pack_metadata_only:
            rn_string += f'\n#### Integrations\n##### {self.pack}\n- Documentation and metadata improvements.\n'
            return rn_string
        rn_template_as_dict: dict = {}
        for content_name, data in sorted(changed_items.items(),
                                         key=lambda x: RN_HEADER_BY_FILE_TYPE[x[1].get('type', '')] if x[1].get('type')
                                         else ''):  # Sort RN by header
            desc = data.get('description', '')
            is_new_file = data.get('is_new_file', False)
            _type = data.get('type', '')
            from_version = data.get('fromversion', '')
            # Skipping the invalid files
            if not _type or content_name == 'N/A':
                continue
            rn_desc = self.build_rn_desc(_type=_type, content_name=content_name, desc=desc, is_new_file=is_new_file,
                                         text=self.text, from_version=from_version)

            header = f'\n#### {RN_HEADER_BY_FILE_TYPE[_type]}\n'
            rn_template_as_dict[header] = rn_template_as_dict.get(header, '') + rn_desc

        for key, val in rn_template_as_dict.items():
            rn_string = f"{rn_string}{key}{val}"

        return rn_string

    def build_rn_desc(self, _type, content_name, desc, is_new_file, text, from_version=''):
        if _type in (FileType.CONNECTION, FileType.INCIDENT_TYPE, FileType.REPUTATION, FileType.LAYOUT,
                     FileType.INCIDENT_FIELD, FileType.INDICATOR_FIELD):
            rn_desc = f'- **{content_name}**\n'
        else:
            if is_new_file:
                rn_desc = f'##### New: {content_name}\n- {desc}'
                if from_version:
                    rn_desc += f' (Available from Cortex XSOAR {from_version}).'
                rn_desc += '\n'
            else:
                rn_desc = f'##### {content_name}\n'
                if self.update_type == 'maintenance':
                    rn_desc += '- Maintenance and stability enhancements.\n'
                elif self.update_type == 'documentation':
                    rn_desc += '- Documentation and metadata improvements.\n'
                else:
                    rn_desc += f'- {text or "%%UPDATE_RN%%"}\n'

        return rn_desc

    def update_existing_rn(self, current_rn, changed_files):
        new_rn = current_rn
        for content_name, data in sorted(changed_files.items(), reverse=True):
            is_new_file = data.get('is_new_file')
            desc = data.get('description', '')
            _type = data.get('type', '')

            if _type is None:
                continue

            _header_by_type = RN_HEADER_BY_FILE_TYPE.get(_type)

            if _type in (FileType.CONNECTION, FileType.INCIDENT_TYPE, FileType.REPUTATION, FileType.LAYOUT,
                         FileType.INCIDENT_FIELD):
                rn_desc = f'\n- **{content_name}**'
            else:
                rn_desc = f'\n##### New: {content_name}\n- {desc}\n' if is_new_file \
                    else f'\n##### {content_name}\n- %%UPDATE_RN%%\n'

            if _header_by_type in current_rn:
                if content_name in current_rn:
                    continue
                else:
                    self.existing_rn_changed = True
                    rn_parts = new_rn.split(_header_by_type)
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = f"{rn_parts[0]}{_header_by_type}{new_rn_part}{rn_parts[1]}"
                    else:
                        new_rn = ''.join(rn_parts) + new_rn_part
            else:
                self.existing_rn_changed = True
                if _header_by_type in new_rn:
                    rn_parts = new_rn.split(_header_by_type)
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = f"{rn_parts[0]}{_header_by_type}{new_rn_part}{rn_parts[1]}"
                else:
                    new_rn_part = f'\n#### {_header_by_type}{rn_desc}'
                    new_rn += new_rn_part
        return new_rn

    def create_markdown(self, release_notes_path: str, rn_string: str, changed_files: dict,
                        docker_image_name: Optional[str]):
        if os.path.exists(release_notes_path) and self.update_type is not None:
            print_warning(f"Release notes were found at {release_notes_path}. Skipping")
        elif self.update_type is None and self.specific_version is None:
            current_rn = get_latest_release_notes_text(release_notes_path)
            updated_rn = self.update_existing_rn(current_rn, changed_files)
            updated_rn = self.rn_with_docker_image(updated_rn, docker_image_name)
            with open(release_notes_path, 'w') as fp:
                fp.write(updated_rn)
        else:
            self.existing_rn_changed = True
            updated_rn = self.rn_with_docker_image(rn_string, docker_image_name)
            with open(release_notes_path, 'w') as fp:
                fp.write(updated_rn)

    def rn_with_docker_image(self, rn_string: str, docker_image: Optional[str]) -> str:
        """
        Receives existing release notes, if docker image was updated, adds docker_image to release notes.
        Taking care of cases s.t:
        1) no docker image update have occurred ('docker_image' is None).
        2) Release notes did not contain updated docker image note.
        3) Release notes contained updated docker image notes, with the newest updated docker image.
        4) Release notes contained updated docker image notes, but docker image was updated again since last time
           release notes have been updated.

        Args:
            rn_string (str): The current text contained in the release note.
            docker_image (Optional[str]): The docker image str, if given.
        Returns:
            (str): The release notes, with the most updated docker image release note, if given.
        """
        if not docker_image:
            return rn_string
        docker_image_str = f'- Updated the Docker image to: *{docker_image}*.'
        if docker_image_str in rn_string:
            return rn_string
        self.existing_rn_changed = True
        if '- Updated the Docker image to' not in rn_string:
            return rn_string + f'{docker_image_str}\n'
        update_docker_image_regex = r'- Updated the Docker image to: \*.*\*\.'
        updated_rn = re.sub(update_docker_image_regex, docker_image_str, rn_string)
        self.existing_rn_changed = True
        return updated_rn


def get_file_description(path, file_type):
    if not os.path.isfile(path):
        print_warning(f'Cannot get file description: "{path}" file does not exist')
        return ''

    elif file_type in (FileType.PLAYBOOK, FileType.INTEGRATION):
        yml_file = get_yaml(path)
        return yml_file.get('description', '')

    elif file_type == FileType.SCRIPT:
        yml_file = get_yaml(path)
        return yml_file.get('comment', '')

    elif file_type in (FileType.CLASSIFIER, FileType.REPORT, FileType.WIDGET, FileType.DASHBOARD):
        json_file = get_json(path)
        return json_file.get('description', '')

    return '%%UPDATE_RN%%'


def update_api_modules_dependents_rn(_pack, pre_release, update_type, added, modified, id_set_path=None, text=''):
    print_warning("Changes introduced to APIModule, trying to update dependent integrations.")
    if not id_set_path:
        if not os.path.isfile(DEFAULT_ID_SET_PATH):
            print_error("Failed to update integrations dependent on the APIModule pack - no id_set.json is "
                        "available. Please run `demisto-sdk create-id-set` to generate it, and rerun this command.")
            return
        id_set_path = DEFAULT_ID_SET_PATH
    with open(id_set_path, 'r') as conf_file:
        id_set = json.load(conf_file)
    api_module_set = get_api_module_ids(added)
    api_module_set = api_module_set.union(get_api_module_ids(modified))
    integrations = get_api_module_integrations_set(api_module_set, id_set.get('integrations', []))
    for integration in integrations:
        integration_path = integration.get('file_path')
        integration_pack = integration.get('pack')
        update_pack_rn = UpdateRN(pack_path=integration_pack, update_type=update_type,
                                  modified_files_in_pack={integration_path}, pre_release=pre_release,
                                  added_files=set(), pack=integration_pack, text=text)
        update_pack_rn.execute_update()


def check_docker_image_changed(added_or_modified_yml):
    try:
        diff = run_command(f'git diff origin/master -- {added_or_modified_yml}', exit_on_error=False)
    except RuntimeError as e:
        if any(['is outside repository' in exp for exp in e.args]):
            return None
        else:
            print_warning(f'skipping docker image check, Encountered the following error:\n{e.args[0]}')
            return None
    else:
        diff_lines = diff.splitlines()
        for diff_line in diff_lines:
            if '+  dockerimage:' in diff_line:  # search whether exists a line that notes that the Docker image was
                # changed.
                return diff_line.split()[-1]
        return None


def get_from_version_at_update_rn(path: str):
    """
    Args:
        path (str): path to yml file, if exists

    Returns:
            str. Fromversion if there fromversion key in the yml file.

    """
    if not os.path.isfile(path):
        print_warning(f'Cannot get file fromversion: "{path}" file does not exist')
        return
    return get_from_version(path)
