"""
This script is used to create a release notes template
"""
import copy
import errno
import json
import os
import re
from distutils.version import LooseVersion
from typing import Optional, Tuple, Union

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, DEFAULT_ID_SET_PATH,
    IGNORED_PACK_NAMES, RN_HEADER_BY_FILE_TYPE, FileType)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               get_api_module_ids,
                                               get_api_module_integrations_set,
                                               get_definition_name,
                                               get_from_version, get_json,
                                               get_latest_release_notes_text,
                                               get_pack_name, get_remote_file,
                                               get_yaml, pack_name_to_path,
                                               print_color, print_error,
                                               print_warning, run_command)


class UpdateRN:
    def __init__(self, pack_path: str, update_type: Union[str, None], modified_files_in_pack: set, added_files: set,
                 specific_version: str = None, pre_release: bool = False, pack: str = None,
                 pack_metadata_only: bool = False, text: str = '', existing_rn_version_path: str = '',
                 is_force: bool = False, is_bc: bool = False):
        self.pack = pack if pack else get_pack_name(pack_path)
        self.update_type = update_type
        self.pack_path = pack_path
        # renamed files will appear in the modified list as a tuple: (old path, new path)
        modified_files_in_pack = {file_[1] if isinstance(file_, tuple) else file_ for file_ in modified_files_in_pack}
        self.modified_files_in_pack = set()
        for file_path in modified_files_in_pack:
            self.modified_files_in_pack.add(self.change_image_or_desc_file_path(file_path))

        self.added_files = added_files
        self.pre_release = pre_release
        self.specific_version = specific_version
        self.existing_rn_changed = False
        self.text = text
        self.existing_rn_version_path = existing_rn_version_path
        self.should_delete_existing_rn = False
        self.pack_metadata_only = pack_metadata_only
        self.is_force = is_force
        self.git_util = GitUtil(repo=Content.git())
        self.main_branch = self.git_util.handle_prev_ver()[1]
        self.metadata_path = os.path.join(self.pack_path, 'pack_metadata.json')
        self.master_version = self.get_master_version()
        self.rn_path = ''
        self.is_bc = is_bc
        self.bc_path = ''

    @staticmethod
    def change_image_or_desc_file_path(file_path: str) -> str:
        """ Changes image and description file paths to the corresponding yml file path.
            if a non-image or description file path is given, it remains unchanged.

            :param file_path: The file path to check

            :rtype: ``str``
            :return
                The new file path if was changed
        """
        if file_path.endswith('_image.png'):
            return file_path.replace('_image.png', '.yml')

        elif file_path.endswith('_description.md'):
            return file_path.replace('_description.md', '.yml')

        return file_path

    def handle_existing_rn_version_path(self, rn_path: str) -> str:
        """ Checks whether the existing RN version path exists and return it's content.

            :param rn_path: The rn path to check

            :rtype: ``str``
            :return
                The content of the rn
        """
        if self.existing_rn_version_path:
            self.should_delete_existing_rn = self.existing_rn_version_path != rn_path
            try:
                with open(self.existing_rn_version_path, 'r') as f:
                    return f.read()
            except Exception as e:
                print_error(f'Failed to load the previous release notes file content: {e}')
        return ''

    def execute_update(self) -> bool:
        """ Obtains the information needed in order to update the pack and executes the update.

            :rtype: ``bool``
            :return
                Whether the RN was updated successfully or not
        """
        if self.pack in IGNORED_PACK_NAMES:
            print_warning(f"Release notes are not required for the {self.pack} pack since this pack"
                          f" is not versioned.")
            return False

        new_version, new_metadata = self.get_new_version_and_metadata()
        rn_path = self.get_release_notes_path(new_version)
        self.check_rn_dir(rn_path)
        self.rn_path = rn_path
        self.find_added_pack_files()
        changed_files = {}
        for packfile in self.modified_files_in_pack:
            file_name, file_type = self.get_changed_file_name_and_type(packfile)
            if 'yml' in packfile and file_type in [FileType.INTEGRATION, FileType.BETA_INTEGRATION,
                                                   FileType.SCRIPT] and packfile not in self.added_files:
                docker_image_name: Optional[str] = check_docker_image_changed(main_branch=self.main_branch, packfile=packfile)
            else:
                docker_image_name = None
            changed_files[(file_name, file_type)] = {
                'description': get_file_description(packfile, file_type),
                'is_new_file': packfile in self.added_files,
                'fromversion': get_from_version_at_update_rn(packfile),
                'dockerimage': docker_image_name,
                'path': packfile
            }
        return self.create_pack_rn(rn_path, changed_files, new_metadata, new_version)

    def create_pack_rn(self, rn_path: str, changed_files: dict, new_metadata: dict, new_version: str) -> bool:
        """ Checks whether the pack requires a new rn and if so, creates it.

            :param
                rn_path (str): The rn path
                changed_files (dict): The changed files details
                new_metadata (dict): The new pack metadata
                new_version (str): The new version str representation, e.g 1.0.2, 1.11.2 etc.


            :rtype: ``bool``
            :return
                Whether the RN was updated successfully or not
        """
        rn_string = self.handle_existing_rn_version_path(rn_path)
        if not rn_string:
            rn_string = self.build_rn_template(changed_files)
        if len(rn_string) > 0 or self.is_force:
            if self.is_bump_required():
                self.write_metadata_to_file(new_metadata)
            self.create_markdown(rn_path, rn_string, changed_files)
            self.build_rn_config_file(new_version)
            try:
                run_command(f'git add {rn_path}', exit_on_error=False)
            except RuntimeError:
                print_warning(f'Could not add the release note files to git: {rn_path}')
            if self.is_bc and self.bc_path:
                try:
                    run_command(f'git add {self.bc_path}', exit_on_error=False)
                except RuntimeError:
                    print_warning(f'Could not add the release note config file to git: {rn_path}')
            if self.existing_rn_changed:
                print_color(f"Finished updating release notes for {self.pack}.", LOG_COLORS.GREEN)
                if not self.text:
                    print_color(f"\nNext Steps:\n - Please review the "
                                f"created release notes found at {rn_path} and document any changes you "
                                f"made by replacing '%%UPDATE_RN%%'.\n - Commit "
                                f"the new release notes to your branch.\nFor information regarding proper"
                                f" format of the release notes, please refer to "
                                f"https://xsoar.pan.dev/docs/integrations/changelog", LOG_COLORS.GREEN)
                return True
            else:
                print_color(f"No changes to {self.pack} pack files were detected from the previous time "
                            "this command was run. The release notes have not been "
                            "changed.", LOG_COLORS.GREEN)
        else:
            print_color("No changes which would belong in release notes were detected.", LOG_COLORS.YELLOW)
        return False

    def build_rn_config_file(self, new_version: str) -> None:
        """
        Builds RN config file if needed. Currently, we use RN config file only for cases where version has breaking
        changes.
        Args:
            new_version (str): The new version number representation, e.g 1.2.1, 1.22.1, etc.

        Returns:
            (None): Creates/updates config file with BC entries, if -bc flag was given.
        """
        # Currently, we only use config file if version is BC. If version is not BC no need to create config file.
        if not self.is_bc:
            return
        bc_file_path: str = f'''{self.pack_path}/ReleaseNotes/{new_version.replace('.', '_')}.json'''
        self.bc_path = bc_file_path
        bc_file_data: dict = dict()
        if os.path.exists(bc_file_path):
            with open(bc_file_path, 'r') as f:
                bc_file_data = json.loads(f.read())
        bc_file_data['breakingChanges'] = True
        bc_file_data['breakingChangesNotes'] = bc_file_data.get('breakingChangesNotes')
        with open(bc_file_path, 'w') as f:
            f.write(json.dumps(bc_file_data))
        print_color(f'Finished creating config file for RN version {new_version}.\n'
                    'If you wish only specific text to be shown as breaking changes, please fill the '
                    '`breakingChangesNotes` field with the appropriate breaking changes text.', LOG_COLORS.GREEN)

    def get_new_version_and_metadata(self) -> Tuple[str, dict]:
        """
            Gets the new version and the new metadata after version bump or by getting it from the pack metadata if
            bump is not required.

            :rtype: ``(str, dict)``
            :return: The new version and new metadata dictionary
        """
        if self.is_bump_required():
            if self.update_type is None:
                self.update_type = "revision"
            new_version, new_metadata = self.bump_version_number(self.specific_version, self.pre_release)
            if self.is_force:
                print_color(f"Bumping {self.pack} to version: {new_version}",
                            LOG_COLORS.NATIVE)
            else:
                print_color(f"Changes were detected. Bumping {self.pack} to version: {new_version}",
                            LOG_COLORS.NATIVE)
        else:
            new_metadata = self.get_pack_metadata()
            new_version = new_metadata.get('currentVersion', '99.99.99')
        return new_version, new_metadata

    def _does_pack_metadata_exist(self) -> bool:
        """ Check if pack_metadata.json exists

            :rtype: ``bool``
            :return
                Whether the pack metadata exists
        """
        if not os.path.isfile(self.metadata_path):
            print_error(f'"{self.metadata_path}" file does not exist, create one in the root of the pack')
            return False

        return True

    def get_master_version(self) -> str:
        """
            Gets the current version from origin/master or origin/main if available, otherwise return '0.0.0'.

            :rtype: ``str``
            :return
                The master version

        """
        master_current_version = '0.0.0'
        master_metadata = None
        try:
            master_metadata = get_remote_file(self.metadata_path, tag=self.main_branch)
        except Exception as e:
            print_error(f"master branch is unreachable.\n The reason is:{e} \n "
                        f"The updated version will be taken from local metadata file instead of master")
        if master_metadata:
            master_current_version = master_metadata.get('currentVersion', '0.0.0')
        return master_current_version

    def is_bump_required(self) -> bool:
        """
            Checks if the currentVersion in the pack metadata has been changed or not. Additionally, it will verify
            that there is no conflict with the currentVersion in then Master branch.

            :rtype: ``bool``
            :return
                Whether a version bump is required
        """
        try:
            if self.only_docs_changed() and not self.is_force:
                return False
            new_metadata = self.get_pack_metadata()
            new_version = new_metadata.get('currentVersion', '99.99.99')
            if LooseVersion(self.master_version) >= LooseVersion(new_version):
                return True
            return False
        except RuntimeError as e:
            raise RuntimeError(f"Unable to locate a pack with the name {self.pack} in the git diff.\n"
                               f"Please verify the pack exists and the pack name is correct.") from e

    def only_docs_changed(self) -> bool:
        """
            Checks if the only files that were changed are documentation files.

            :rtype: ``bool``
            :return
                Whether only the docs were changed
        """
        changed_files = self.added_files.union(self.modified_files_in_pack)
        changed_files_copy = copy.deepcopy(changed_files)  # copying as pop will leave the file out of the set
        if (len(changed_files) == 1 and 'README' in changed_files_copy.pop()) or \
                (all('README' in file or ('.png' in file and '_image.png' not in file) for file in changed_files)):
            return True
        return False

    def find_added_pack_files(self):
        """
            Checks if the added files in the given pack require RN and if so, adds them to the modified files in the
            pack.
        """
        for a_file in self.added_files:
            if self.pack in a_file:
                if any(item in a_file for item in ALL_FILES_VALIDATION_IGNORE_WHITELIST):
                    continue
                else:
                    self.modified_files_in_pack.add(self.change_image_or_desc_file_path(a_file))

    def get_release_notes_path(self, input_version: str) -> str:
        """ Gets the release notes path.

            :param input_version: The new rn version

            :rtype: ``bool``
            :return
            Whether the RN was updated successfully or not
        """
        _new_version = input_version.replace('.', '_')
        new_version = _new_version.replace('_prerelease', '')
        return os.path.join(self.pack_path, 'ReleaseNotes', f'{new_version}.md')

    @staticmethod
    def get_display_name(file_path) -> str:
        """ Gets the file name from the pack yml file.

            :param file_path: The pack yml file path

            :rtype: ``str``
            :return
            The display name
        """
        struct = StructureValidator(file_path=file_path, is_new_file=True, predefined_scheme=find_type(file_path))
        file_data = struct.load_data_from_file()
        if 'display' in file_data:
            name = file_data.get('display', None)
        elif 'layout' in file_data and isinstance(file_data['layout'], dict):
            name = file_data['layout'].get('id')
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
    def find_corresponding_yml(file_path) -> str:
        """ Gets the pack's corresponding yml file from the python/yml file.

            :param file_path: The pack python/yml file

            :rtype: ``str``
            :return
            The path to the pack's yml file
        """
        if file_path.endswith('.py'):
            yml_filepath = file_path.replace('.py', '.yml')
        else:
            yml_filepath = file_path
        return yml_filepath

    def get_changed_file_name_and_type(self, file_path) -> Tuple[str, Optional[FileType]]:
        """ Gets the changed file name and type.

            :param file_path: The file path

            :rtype: ``str, FileType``
            :return
            The changed file name and type
        """
        _file_type = None
        file_name = 'N/A'

        if self.pack + '/' in file_path and ('README' not in file_path):
            _file_path = self.find_corresponding_yml(file_path)
            file_name = self.get_display_name(_file_path)
            _file_type = find_type(_file_path)

        return file_name, _file_type

    def get_pack_metadata(self) -> dict:
        """ Gets the pack metadata.

            :rtype: ``dict``
            :return
            The pack metadata dictionary
        """
        try:
            data_dictionary = get_json(self.metadata_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(f'Pack {self.pack} was not found. Please verify the pack name is correct.') from e
        return data_dictionary

    def bump_version_number(self, specific_version: str = None, pre_release: bool = False) -> Tuple[str, dict]:
        """ Increases the version number by user input or update type.

            :param
                specific_version: The specific version to change the version to
                pre_release: Indicates that the change should be designated a pre-release version

            :rtype: ``str, dict``
            :return
            The new version number (for example: 1.0.3) and the new pack metadata after version bump
        """
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

    def write_metadata_to_file(self, metadata_dict: dict):
        """ Writes the new metadata to the pack metadata file.

            :param
                metadata_dict: The new metadata to write

        """
        if self._does_pack_metadata_exist():
            with open(self.metadata_path, 'w') as file_path:
                json.dump(metadata_dict, file_path, indent=4)
                print_color(f"Updated pack metadata version at path : {self.metadata_path}",
                            LOG_COLORS.GREEN)

    @staticmethod
    def check_rn_dir(rn_path: str):
        """ Checks whether the release notes folder exists and if not creates it.

            :param rn_path: The RN path to check/create

        """
        if not os.path.exists(os.path.dirname(rn_path)):
            try:
                os.makedirs(os.path.dirname(rn_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def build_rn_template(self, changed_items: dict) -> str:
        """ Builds the new release notes template.

            :param
                changed_items: The changed items data dictionary

            :rtype: ``str``
            :return
            The new release notes template
        """
        rn_string = ''

        if self.pack_metadata_only:
            rn_string += f'\n#### Integrations\n##### {self.pack}\n- Documentation and metadata improvements.\n'
            return rn_string
        rn_template_as_dict: dict = {}
        if self.is_force:
            rn_string = self.build_rn_desc(content_name=self.pack, text=self.text)
        # changed_items.items() looks like that: [((name, type), {...}), (name, type), {...}] and we want to sort
        # them by type (x[0][1])
        for (content_name, _type), data in sorted(changed_items.items(),
                                                  key=lambda x: RN_HEADER_BY_FILE_TYPE[x[0][1]] if x[0] and x[0][1]
                                                  else ''):  # Sort RN by header
            desc = data.get('description', '')
            is_new_file = data.get('is_new_file', False)
            from_version = data.get('fromversion', '')
            docker_image = data.get('dockerimage')
            path = data.get('path')
            # Skipping the invalid files
            if not _type or content_name == 'N/A':
                continue
            rn_desc = self.build_rn_desc(_type=_type, content_name=content_name, desc=desc, is_new_file=is_new_file,
                                         text=self.text, docker_image=docker_image, from_version=from_version,
                                         path=path)

            header = f'\n#### {RN_HEADER_BY_FILE_TYPE[_type]}\n'
            rn_template_as_dict[header] = rn_template_as_dict.get(header, '') + rn_desc

        for key, val in rn_template_as_dict.items():
            rn_string = f"{rn_string}{key}{val}"

        return rn_string

    def build_rn_desc(self, _type: FileType = None, content_name: str = '', desc: str = '', is_new_file: bool = False,
                      text: str = '', docker_image: Optional[str] = '', from_version: str = '', path: str = '') -> str:
        """ Builds the release notes description.

            :param
                _type: The file type
                content_name: The pack name
                desc: The pack description
                is_new_file: True if the file is new
                text: Text to add to the release notes files
                from_version: From version

            :rtype: ``str``
            :return
            The release notes description
        """
        if _type in (FileType.CONNECTION, FileType.INCIDENT_TYPE, FileType.REPUTATION, FileType.LAYOUT,
                     FileType.INCIDENT_FIELD, FileType.INDICATOR_FIELD):
            rn_desc = f'- **{content_name}**\n'

        elif _type in (FileType.GENERIC_TYPE, FileType.GENERIC_FIELD):
            definition_name = get_definition_name(path, self.pack_path)
            rn_desc = f'- **({definition_name}) - {content_name}**\n'
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
        if docker_image:
            rn_desc += f'- Updated the Docker image to: *{docker_image}*.\n'
        return rn_desc

    def update_existing_rn(self, current_rn, changed_files) -> str:
        """ Update the existing release notes.

            :param
                current_rn: The existing rn
                changed_files: The new data to add

            :rtype: ``str``
            :return
            The updated release notes
        """
        update_docker_image_regex = r'- Updated the Docker image to: \*.*\*\.'
        # Deleting old entry for docker images, will re-write later, this allows easier generating of updated rn.
        current_rn_without_docker_images = re.sub(update_docker_image_regex, '', current_rn)
        new_rn = current_rn_without_docker_images
        # changed_files.items() looks like that: [((name, type), {...}), (name, type), {...}] and we want to sort
        # them by name (x[0][0])
        for (content_name, _type), data in sorted(changed_files.items(),
                                                  key=lambda x: x[0][0] if x[0][0] else '', reverse=True):
            is_new_file = data.get('is_new_file')
            desc = data.get('description', '')
            docker_image = data.get('dockerimage')
            path = data.get('path')

            if _type is None:
                continue

            _header_by_type = RN_HEADER_BY_FILE_TYPE.get(_type)
            if _type in (FileType.CONNECTION, FileType.INCIDENT_TYPE, FileType.REPUTATION, FileType.LAYOUT,
                         FileType.INCIDENT_FIELD, FileType.JOB):
                rn_desc = f'\n- **{content_name}**'

            elif _type in (FileType.GENERIC_TYPE, FileType.GENERIC_FIELD):
                definition_name = get_definition_name(path, self.pack_path)
                rn_desc = f'\n- **({definition_name}) - {content_name}**'

            else:
                rn_desc = f'\n##### New: {content_name}\n- {desc}\n' if is_new_file \
                    else f'\n##### {content_name}\n- %%UPDATE_RN%%\n'
            if docker_image:
                rn_desc += f'- Updated the Docker image to: *{docker_image}*.'

            if _header_by_type and _header_by_type in current_rn_without_docker_images:
                if content_name in current_rn_without_docker_images:
                    if docker_image:
                        new_rn = self.handle_existing_rn_with_docker_image(new_rn, _header_by_type, docker_image,
                                                                           content_name)
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
        if new_rn != current_rn:
            self.existing_rn_changed = True
        return new_rn

    @staticmethod
    def handle_existing_rn_with_docker_image(new_rn: str, header_by_type: str, docker_image: str,
                                             content_name: str) -> str:
        """
        Receives the new RN to be written, performs operations to add the docker image to the given RN.
        Args:
            new_rn (str): new RN.
            header_by_type (str): Header of the RN to add docker image to, e.g 'Integrations', 'Scripts'
            docker_image (str): Docker image to add
            content_name (str): The content name to add the docker image entry to, e.g integration name, script name.

        Returns:
            (str): Updated RN
        """
        # Writing or re-writing docker image to release notes.
        rn_parts = new_rn.split(header_by_type)
        new_rn_part = f'- Updated the Docker image to: *{docker_image}*.'
        if len(rn_parts) > 1:
            # Splitting again by content name to append the docker image release note to corresponding
            # content entry only
            content_parts = rn_parts[1].split(f'{content_name}\n')
            new_rn = f'{rn_parts[0]}{header_by_type}{content_parts[0]}{content_name}\n{new_rn_part}\n' \
                     f'{content_parts[1]}'
        else:
            print_warning(f'Could not parse release notes {new_rn} by header type: {header_by_type}')
        return new_rn

    def create_markdown(self, release_notes_path: str, rn_string: str, changed_files: dict):
        """ Creates the new markdown and writes it to the release notes file.

            :param
                release_notes_path: The release notes file path
                rn_string: The rn data (if exists)
                changed_files: The changed files details
                docker_image_name: The docker image name

        """
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

    def rn_with_docker_image(self, rn_string: str, docker_image: Optional[str]) -> str:
        """
            Receives existing release notes, if docker image was updated, adds docker_image to release notes.
            Taking care of cases s.t:
            1) no docker image update have occurred ('docker_image' is None).
            2) Release notes did not contain updated docker image note.
            3) Release notes contained updated docker image notes, with the newest updated docker image.
            4) Release notes contained updated docker image notes, but docker image was updated again since last time
               release notes have been updated.

            param:
                rn_string (str): The current text contained in the release note
                docker_image (Optional[str]): The docker image str, if given

            :rtype: ``str``
            :return
                The release notes, with the most updated docker image release note, if given
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


def get_file_description(path, file_type) -> str:
    """ Gets the file description.

        :param
            path: The file path
            file_type: The file type

        :rtype: ``str``
        :return
        The file description if exists otherwise returns %%UPDATE_RN%%
    """
    if not os.path.isfile(path):
        print_warning(f'Cannot get file description: "{path}" file does not exist')
        return ''

    elif file_type in (FileType.PLAYBOOK, FileType.INTEGRATION):
        yml_file = get_yaml(path)
        return yml_file.get('description', '')

    elif file_type == FileType.SCRIPT:
        yml_file = get_yaml(path)
        return yml_file.get('comment', '')

    elif file_type in (FileType.CLASSIFIER, FileType.REPORT, FileType.WIDGET, FileType.DASHBOARD, FileType.JOB):
        json_file = get_json(path)
        return json_file.get('description', '')

    return '%%UPDATE_RN%%'


def update_api_modules_dependents_rn(pre_release: bool, update_type: Union[str, None],
                                     added: Union[list, set], modified: Union[list, set],
                                     id_set_path: Optional[str] = None, text: str = '') -> set:
    """ Updates release notes for any pack that depends on API module that has changed.

        :param
            pre_release: The file type
            update_type: The update type
            added: The added files
            modified: The modified files
            id_set_path: The id set path
            text: Text to add to the release notes files

        :rtype: ``set``
        :return
        A set of updated packs
    """
    total_updated_packs: set = set()
    if not id_set_path:
        if not os.path.isfile(DEFAULT_ID_SET_PATH):
            print_error("Failed to update integrations dependent on the APIModule pack - no id_set.json is "
                        "available. Please run `demisto-sdk create-id-set` to generate it, and rerun this command.")
            return total_updated_packs
        id_set_path = DEFAULT_ID_SET_PATH
    with open(id_set_path, 'r') as conf_file:
        id_set = json.load(conf_file)
    api_module_set = get_api_module_ids(added)
    api_module_set = api_module_set.union(get_api_module_ids(modified))
    print_warning(f"Changes were found in the following APIModules: {api_module_set}, updating all dependent "
                  f"integrations.")
    integrations = get_api_module_integrations_set(api_module_set, id_set.get('integrations', []))
    for integration in integrations:
        integration_path = integration.get('file_path')
        integration_pack = integration.get('pack')
        integration_pack_path = pack_name_to_path(integration_pack)
        update_pack_rn = UpdateRN(pack_path=integration_pack_path, update_type=update_type,
                                  modified_files_in_pack={integration_path}, pre_release=pre_release,
                                  added_files=set(), pack=integration_pack, text=text)
        updated = update_pack_rn.execute_update()
        if updated:
            total_updated_packs.add(integration_pack)
    return total_updated_packs


def check_docker_image_changed(main_branch: str, packfile: str) -> Optional[str]:
    """ Checks whether the docker image was changed in master.

        :param
            main_branch: The git main branch
            packfile: The added or modified yml path

        :rtype: ``Optional[str]``
        :return
        The latest docker image
    """
    try:
        diff = run_command(f'git diff {main_branch} -- {packfile}', exit_on_error=False)
    except RuntimeError as e:
        if any(['is outside repository' in exp for exp in e.args]):
            return None
        else:
            print_warning(f'skipping docker image check, Encountered the following error:\n{e.args[0]}')
            return None
    else:
        diff_lines = diff.splitlines()
        for diff_line in diff_lines:
            if 'dockerimage:' in diff_line:  # search whether exists a line that notes that the Docker image was
                # changed.
                split_line = diff_line.split()
                if split_line[0] == '+':
                    return split_line[-1]
        return None


def get_from_version_at_update_rn(path: str) -> Optional[str]:
    """
        param:
            path (str): path to yml file, if exists

        :rtype: ``Optional[str]``
        :return:
            Fromversion if there is a fromversion key in the yml file

    """
    if not os.path.isfile(path):
        print_warning(f'Cannot get file fromversion: "{path}" file does not exist')
        return None
    return get_from_version(path)
