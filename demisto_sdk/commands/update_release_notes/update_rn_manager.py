import os
from typing import Optional, Tuple

import git
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK, SKIP_RELEASE_NOTES_FOR_TYPES)
from demisto_sdk.commands.common.tools import (LOG_COLORS,
                                               filter_files_by_type,
                                               filter_files_on_pack,
                                               get_pack_name,
                                               get_pack_names_from_files,
                                               print_color,
                                               print_warning)
from demisto_sdk.commands.update_release_notes.update_rn import (
    UpdateRN, update_api_modules_dependents_rn)
from demisto_sdk.commands.validate.validate_manager import ValidateManager


class UpdateReleaseNotesManager:
    def __init__(self, user_input: Optional[str] = None, update_type: Optional[str] = None,
                 pre_release: bool = False, is_all: Optional[bool] = False, text: Optional[str] = None,
                 specific_version: Optional[str] = None, id_set_path: Optional[str] = None,
                 prev_ver: Optional[str] = None, is_force: bool = False):
        self.given_pack = user_input
        self.changed_packs_from_git: set = set()
        self.update_type = update_type
        self.pre_release: bool = False if pre_release is None else pre_release
        # update release notes to every required pack if not specified.
        self.is_all = True if not self.given_pack else is_all
        self.text: str = '' if text is None else text
        self.is_force = is_force
        self.specific_version = specific_version
        self.id_set_path = id_set_path
        self.prev_ver = prev_ver
        self.packs_existing_rn: dict = {}
        self.total_updated_packs: set = set()
        # When a user choose a specific pack to update rn, the -g flag should not be passed
        if self.given_pack and self.is_all:
            raise ValueError('Please remove the -g flag when specifying only one pack.')
        self.rn_path = None

    def manage_rn_update(self):
        """
            Manages the entire update release notes process.
        """
        print_color('Starting to update release notes.', LOG_COLORS.NATIVE)
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
        if len(self.total_updated_packs) > 1:
            print_color('\nSuccessfully updated the following packs:\n' + '\n'.join(self.total_updated_packs),
                        LOG_COLORS.GREEN)

    def get_git_changed_files(self) -> Tuple[set, set, set, set]:
        """ Get the changed files from git (added, modified, old format, metadata).

            :return:
                4 sets:
                - The filtered modified files (including the renamed files)
                - The filtered added files
                - The changed metadata files
                - The modified old-format files (legacy unified python files)
        """
        try:
            validate_manager = ValidateManager(skip_pack_rn_validation=True, prev_ver=self.prev_ver,
                                               silence_init_prints=True, skip_conf_json=True, check_is_unskipped=False)
            if not validate_manager.git_util:  # in case git utils can't be initialized.
                raise FileNotFoundError
            validate_manager.setup_git_params()
            return validate_manager.get_changed_files_from_git()
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, FileNotFoundError) as e:
            raise FileNotFoundError(
                "You are not running `demisto-sdk update-release-notes` command in the content repository.\n"
                "Please run `cd content` from your terminal and run the command again") from e

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
        # The user gave a path to the api module which was changed or he didn't give a path but some api modules
        # have changed.
        api_module_was_given = self.given_pack and API_MODULES_PACK in self.given_pack
        api_module_changed_in_git = self.changed_packs_from_git and API_MODULES_PACK in self.changed_packs_from_git

        if api_module_was_given or api_module_changed_in_git:
            updated_packs = update_api_modules_dependents_rn(self.pre_release, self.update_type, added_files,
                                                             modified_files, self.id_set_path, self.text)
            self.total_updated_packs = self.total_updated_packs.union(updated_packs)

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
            self.create_pack_release_notes(self.given_pack, filtered_modified_files, filtered_added_files,
                                           old_format_files)

        elif self.changed_packs_from_git:  # update all changed packs
            for pack in self.changed_packs_from_git:
                if 'APIModules' in pack:  # We already handled Api Modules so we can skip it.
                    continue
                self.create_pack_release_notes(pack, filtered_modified_files, filtered_added_files, old_format_files)
        else:
            print_warning('No changes that require release notes were detected. If such changes were made, '
                          'please commit the changes and rerun the command.')

    def create_pack_release_notes(self, pack: str, filtered_modified_files: set, filtered_added_files: set,
                                  old_format_files: set):
        """ Creates the release notes for a given pack if was changed.

            :param
                pack: The pack to create release notes for
                filtered_modified_files: A set of filtered modified files
                filtered_added_files: A set of filtered added files
                old_format_files: A set of old formatted files
        """
        existing_rn_version = self.get_existing_rn(pack)
        if existing_rn_version is None:  # New release notes file already found for the pack
            raise RuntimeError(f"New release notes file already found for {pack}. "
                               f"Please update manually or run `demisto-sdk update-release-notes "
                               f"-i {pack}` without specifying the update_type.")
        pack_modified = filter_files_on_pack(pack, filtered_modified_files)
        pack_added = filter_files_on_pack(pack, filtered_added_files)
        pack_old = filter_files_on_pack(pack, old_format_files)

        # Checks if update is required
        if pack_modified or pack_added or pack_old or self.is_force:
            update_pack_rn = UpdateRN(pack_path=f'Packs/{pack}', update_type=self.update_type,
                                      modified_files_in_pack=pack_modified.union(pack_old),
                                      pre_release=self.pre_release,
                                      added_files=pack_added, specific_version=self.specific_version,
                                      text=self.text, is_force=self.is_force,
                                      existing_rn_version_path=existing_rn_version)
            updated = update_pack_rn.execute_update()
            self.rn_path = update_pack_rn.rn_path

            # If new release notes were created add it to the total number of packs that were updated.
            if updated:
                self.total_updated_packs.add(pack)
                # If there is an outdated previous release notes, remove it (for example: User updated his version to
                # 1.0.4 and meanwhile the master version changed to 1.0.4, so we want to remove the user's 1_0_4 file
                # and add a 1_0_5 file.)
                if update_pack_rn.should_delete_existing_rn:
                    os.unlink(self.packs_existing_rn[pack])
        else:
            print_warning(f'Either no changes were found in {pack} pack '
                          f'or the changes found should not be documented in the release notes file.\n'
                          f'If relevant changes were made, please commit the changes and rerun the command.')

    def get_existing_rn(self, pack) -> Optional[str]:
        """ Gets the existing rn of the pack is exists.

            :param
                pack: The pack to check
            :return
                The existing rn version if exists, otherwise an empty string
                None on error when pack has rn already and update type was given
        """
        if pack not in self.packs_existing_rn:
            return ''

        if self.update_type is None:
            return self.packs_existing_rn[pack]
        else:
            return None
