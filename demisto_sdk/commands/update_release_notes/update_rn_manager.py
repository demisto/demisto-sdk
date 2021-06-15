import os
import sys
from typing import Tuple, Set, Optional

import git

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK, SKIP_RELEASE_NOTES_FOR_TYPES)
from demisto_sdk.commands.common.tools import (filter_files_by_type,
                                               filter_files_on_pack,
                                               get_pack_name,
                                               get_pack_names_from_files,
                                               print_error, print_warning)
from demisto_sdk.commands.update_release_notes.update_rn import (
    UpdateRN, update_api_modules_dependents_rn)
from demisto_sdk.commands.validate.validate_manager import ValidateManager


class UpdateReleaseNotesManager:
    def __init__(self, user_input: str = None, update_type: str = None, pre_release: bool = False, is_all: bool = None,
                 text: str = '', specific_version: str = None, id_set_path: str = None, prev_ver: str = None):
        self.given_pack = user_input
        self.changed_packs_from_git: set = set()
        self.update_type = update_type
        self.pre_release = pre_release
        # update release notes to every required pack if not specified.
        self.is_all = True if not self.given_pack else is_all
        self.text = text
        self.specific_version = specific_version
        self.id_set_path = id_set_path
        self.prev_ver = prev_ver
        self.packs_existing_rn: dict = {}

    def manage_rn_update(self):
        """
            Manages the entire update release notes process.
        """
        try:
            # When a user choose a specific pack to update rn, the --all flag should not be passed
            if self.given_pack and self.is_all:
                print_error('Please remove the --all flag when specifying only one pack.')
                sys.exit(0)

            print('Starting to update release notes.')
            # The given_pack can be both path or pack name thus, we extract the pack name from the path if needed.
            if self.given_pack and '/' in self.given_pack:
                self.given_pack = get_pack_name(self.given_pack)  # extract pack from path

            # Find which files were changed from git
            modified_files, added_files, _, old_format_files = self.get_git_changed_files()
            self.changed_packs_from_git = get_pack_names_from_files(modified_files).union(
                get_pack_names_from_files(added_files)).union(get_pack_names_from_files(old_format_files))
            # Check whether the packs have some existing RNs already (created manually or by the command)
            self.check_existing_rn(added_files)

            self.handle_api_module_change(modified_files, added_files)
            self.create_release_notes(modified_files, added_files, old_format_files)
            sys.exit(0)
        except Exception as e:
            print_error(f'An error occurred while updating the release notes: {str(e)}')
            sys.exit(1)

    def get_git_changed_files(self) -> Tuple[set, set, set, set]:
        """ Get the changed files from git (added, modified, old format, metadata)

            :return:
                4 sets:
                - The filtered modified files (including the renamed files)
                - The filtered added files
                - The changed metadata files
                - The modified old-format files (legacy unified python files)
        """
        try:
            validate_manager = ValidateManager(skip_pack_rn_validation=True, prev_ver=self.prev_ver,
                                               silence_init_prints=True)
            validate_manager.setup_git_params()
            return validate_manager.get_changed_files_from_git()
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError):
            print_error("You are not running `demisto-sdk update-release-notes` command in the content repository.\n"
                        "Please run `cd content` from your terminal and run the command again")
            sys.exit(1)

    def check_existing_rn(self, added_files: set):
        """
            Checks whether the packs already have an existing release notes files and adds
            them to the packs_existing_rn dictionary.

            :param added_files: A set of new added files
        """
        for file_path in added_files:
            if 'ReleaseNotes' in file_path:
                self.packs_existing_rn[get_pack_name(file_path)] = file_path

    def handle_api_module_change(self, modified_files: set, added_files: set):
        """ Checks whether the modified file is in the API modules pack and if so, updates every pack which depends
            on that API module.

            :param
                added_files: A set of new added files
                modified_files: A set of modified files
        """
        if (self.given_pack and API_MODULES_PACK in self.given_pack) or \
                (self.changed_packs_from_git and API_MODULES_PACK in self.changed_packs_from_git):

            update_api_modules_dependents_rn(self.given_pack, self.pre_release, self.update_type, added_files,
                                             modified_files, id_set_path=self.id_set_path, text=self.text)

    def create_release_notes(self, modified_files: set, added_files: set, old_format_files: set):
        """ Iterates over the packs which needs an update and creates a release notes for them.

            :param
                modified_files: A set of modified files
                added_files: A set of added files
                old_format_files: A set of old formatted files
        """
        # Certain file types do not require release notes update
        filtered_modified_files = filter_files_by_type(modified_files, skip_file_types=SKIP_RELEASE_NOTES_FOR_TYPES)
        filtered_added_files = filter_files_by_type(added_files, skip_file_types=SKIP_RELEASE_NOTES_FOR_TYPES)
        if self.given_pack:  # A specific pack was chosen to update
            self.changed_packs_from_git = {self.given_pack}
            self.create_pack_release_notes(self.given_pack, filtered_modified_files, filtered_added_files,
                                           old_format_files)

        elif self.changed_packs_from_git:  # update all changed packs
            for pack in self.changed_packs_from_git:
                self.create_pack_release_notes(pack, filtered_modified_files, filtered_added_files, old_format_files)
        else:
            print_warning('No changes that require release notes were detected. If such changes were made, '
                          'please commit the changes and rerun the command')

    def create_pack_release_notes(self, pack: str, filtered_modified_files: set, filtered_added_files: set,
                                  old_format_files: set):
        """ Creates the release notes for a given pack.

            :param
                pack: The pack to create release notes for
                filtered_modified_files: A set of filtered modified files
                filtered_added_files: A set of filtered added files
                old_format_files: A set of old formatted files
        """
        existing_rn_version = self.get_existing_rn(pack)
        if existing_rn_version is None:
            sys.exit(0)
        pack_modified = filter_files_on_pack(pack, filtered_modified_files)
        pack_added = filter_files_on_pack(pack, filtered_added_files)
        pack_old = filter_files_on_pack(pack, old_format_files)

        # Checks if update is required
        if pack_modified or pack_added or pack_old:
            update_pack_rn = UpdateRN(pack_path=f'Packs/{pack}', update_type=self.update_type,
                                      modified_files_in_pack=pack_modified.union(pack_old),
                                      pre_release=self.pre_release,
                                      added_files=pack_added, specific_version=self.specific_version,
                                      text=self.text,
                                      existing_rn_version_path=existing_rn_version)
            updated = update_pack_rn.execute_update()
            # If new release notes were created and if previous release notes existed, remove previous
            if updated and update_pack_rn.should_delete_existing_rn:
                os.unlink(self.packs_existing_rn[pack])
        else:
            print_warning(f'Either no changes were found in {pack} pack '
                          f'or the changes found should not be documented in the release notes file '
                          f'If relevant changes were made, please commit the changes and rerun the command')

    def get_existing_rn(self, pack) -> Optional[str]:
        """ Gets the existing rn of the pack is exists

            :param
                pack: The pack to check
            :return
                The existing rn version
        """
        if pack in self.packs_existing_rn:
            if self.update_type is None:
                return self.packs_existing_rn[pack]
            else:
                print_error(f"New release notes file already found for {pack}. "
                            f"Please update manually or run `demisto-sdk update-release-notes "
                            f"-i {pack}` without specifying the update_type.")
                return None
        return ''
