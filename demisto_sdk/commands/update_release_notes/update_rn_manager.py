from pathlib import Path
from typing import Optional, Tuple

import git

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_pack_name,
    suppress_stdout,
)
from demisto_sdk.commands.content_graph.objects import Pack
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.update_release_notes.update_rn import (
    update_api_modules_dependents_rn,
)
from demisto_sdk.commands.validate.validate_manager import ValidateManager


class UpdateReleaseNotesManager:
    def __init__(
        self,
        user_input: Optional[str] = None,
        update_type: Optional[str] = None,
        pre_release: bool = False,
        is_all: Optional[bool] = False,
        text: Optional[str] = None,
        specific_version: Optional[str] = None,
        prev_ver: Optional[str] = None,
        is_force: bool = False,
        is_bc: bool = False,
    ):
        self.given_pack = user_input
        self.changed_packs_from_git: set = set()
        self.update_type = update_type
        self.pre_release: bool = False if pre_release is None else pre_release
        # update release notes to every required pack if not specified.
        self.is_all = True if not self.given_pack else is_all
        self.text: str = "" if text is None else text
        self.is_force = is_force
        self.specific_version = specific_version
        self.prev_ver = prev_ver
        self.packs_existing_rn: dict = {}
        self.total_updated_packs: set = set()
        # When a user choose a specific pack to update rn, the -g flag should not be passed
        if self.given_pack and self.is_all:
            raise ValueError("Please remove the -g flag when specifying only one pack.")
        self.rn_path: list = list()
        self.is_bc = is_bc

    def get_content_items(self, file_path: str):
        content_items = []
        content_item = BaseContent.from_path(Path(file_path))

        if not isinstance(content_item, (ContentItem, Pack)):
            raise ValueError(f"Could not parse content_item from {file_path}")

        pack = content_item.in_pack  # type: ignore[union-attr]
        content_items.append({pack: content_item})

        return content_items

    def merge_content_items(self, content_items: dict):
        """
        The function iterates through the lists and dictionaries to properly merge the content items based on pack name
        and modification type.
        Return information about content items grouped by pack name and modification type. For example:

        merged_results = {
            'Pack1': {
                'new': ['object_id1', 'object_id2'],
                'modified': ['object_id3']
            },
            'Pack2': {
                'old_format': ['object_id4']
            }
        }
        """
        merged_dict = {}

        for modification_type, pack_items_list in content_items.items():
            for pack_items in pack_items_list:
                for pack_name, content_item in pack_items.items():
                    if pack_name not in merged_dict:
                        merged_dict[pack_name] = {modification_type: [content_item]}
                    else:
                        if modification_type in merged_dict[pack_name]:
                            merged_dict[pack_name][modification_type].extend(
                                [content_item]
                            )
                        else:
                            merged_dict[pack_name][modification_type] = [content_item]
        return merged_dict

    def manage_rn_update(self):
        """
        Manages the entire update release notes process.
        """
        logger.info("Starting to update release notes.")
        content_items: dict = {"new": [], "modified": [], "old_format": []}
        # Find which files were changed from git
        modified_files, added_files, old_format_files = self.get_git_changed_files()

        for file_path in modified_files:
            content_items["modified"].extend(self.get_content_items(file_path))
        for file_path in added_files:
            content_items["new"].extend(self.get_content_items(file_path))
        for file_path in old_format_files:
            content_items["old_format"].extend(self.get_content_items(file_path))

        content = self.merge_content_items(content_items)

        # Check whether the packs have some existing RNs already (created manually or by the command)
        self.check_existing_rn(added_files)
        self.handle_api_module_change(modified_files, added_files, content)

        self.create_release_notes(content)
        if len(self.total_updated_packs) > 1:
            logger.info(
                "\n[green]Successfully updated the following packs:\n"
                + "\n".join(self.total_updated_packs)
                + "[/green]"
            )

    def filter_to_relevant_files(
        self, file_set: set, validate_manager: ValidateManager
    ) -> Tuple[set, set, bool]:
        """
        Given a file set, filter it to only files which require RN and if given, from a specific pack
        """
        filtered_set = set()
        for file in file_set:
            if isinstance(file, tuple):
                file_path = str(file[1])

            else:
                file_path = str(file)

            if self.given_pack:
                file_pack_name = get_pack_name(file_path)
                if not file_pack_name or file_pack_name not in self.given_pack:
                    continue

            filtered_set.add(file)

        return validate_manager.filter_to_relevant_files(filtered_set)

    def filter_files_from_git(
        self,
        modified_files: set,
        added_files: set,
        renamed_files: set,
        validate_manager: ValidateManager,
    ):
        """
        Filter the raw file sets to only the relevant files for RN
        """
        filtered_modified, old_format_files, _ = self.filter_to_relevant_files(
            modified_files, validate_manager
        )
        filtered_renamed, _, _ = self.filter_to_relevant_files(
            renamed_files, validate_manager
        )
        filtered_modified = filtered_modified.union(filtered_renamed)
        filtered_added, new_files_in_old_format, _ = self.filter_to_relevant_files(
            added_files, validate_manager
        )
        old_format_files = old_format_files.union(new_files_in_old_format)
        return filtered_modified, filtered_added, old_format_files

    def setup_validate_manager(self):
        return ValidateManager(
            skip_pack_rn_validation=True,
            prev_ver=self.prev_ver,
            silence_init_prints=True,
            skip_conf_json=True,
            check_is_unskipped=False,
            file_path=self.given_pack,
        )

    def get_git_changed_files(self) -> Tuple[set, set, set]:
        """Get the changed files from git (added, modified, old format, metadata).

        :return:
            - The filtered modified files (including the renamed files)
            - The filtered added files
            - The modified old-format files (legacy unified python files)
        """
        try:
            validate_manager = self.setup_validate_manager()
            if not validate_manager.git_util:  # in case git utils can't be initialized.
                raise git.InvalidGitRepositoryError("unable to connect to git.")
            validate_manager.setup_git_params()
            if self.given_pack:
                with suppress_stdout():
                    # The Validator prints errors which are related to all changed files that
                    # were changed against prev version. When the user is giving a specific pack to update,
                    # we want to suppress the error messages which are related to other packs.
                    (
                        modified_files,
                        added_files,
                        renamed_files,
                    ) = validate_manager.get_unfiltered_changed_files_from_git()
                    return self.filter_files_from_git(
                        modified_files, added_files, renamed_files, validate_manager
                    )

            (
                modified_files,
                added_files,
                renamed_files,
            ) = validate_manager.get_unfiltered_changed_files_from_git()
            return self.filter_files_from_git(
                modified_files, added_files, renamed_files, validate_manager
            )

        except (
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            FileNotFoundError,
        ) as e:
            raise FileNotFoundError(
                "You are not running `demisto-sdk update-release-notes` command in the content repository.\n"
                "Please run `cd content` from your terminal and run the command again"
            ) from e

    def check_existing_rn(self, added_files: set):
        """
        Checks whether the packs already have an existing release notes files and adds
        them to the packs_existing_rn dictionary.

        :param added_files: A set of new added files
        """
        for file_path in added_files:
            if "ReleaseNotes" in file_path:
                self.packs_existing_rn[get_pack_name(file_path)] = file_path

    def handle_api_module_change(
        self, modified_files: set, added_files: set, content: dict
    ):
        """Checks whether the modified file is in the API modules pack and if so, updates every pack which depends
        on that API module.

        :param
            added_files: A set of new added files
            modified_files: A set of modified files
        """
        # We want to handle ApiModules changes when:
        # (1) The user gave a path to the api module which was changed.
        # (2) The user did not give a specific path at all (is_all = True) but some ApiModules were changed.
        api_module_was_given = self.given_pack and API_MODULES_PACK in self.given_pack
        api_module_changed = any(
            pack.name == API_MODULES_PACK for pack, _ in content.items()
        )

        if api_module_was_given or (api_module_changed and self.is_all):
            updated_packs = update_api_modules_dependents_rn(
                self.pre_release,
                self.update_type,
                added_files,
                modified_files,
                self.text,
            )
            self.total_updated_packs = self.total_updated_packs.union(updated_packs)

    def create_release_notes(self, content: dict):
        """Iterates over the packs which needs an update and creates a release notes for them.

        :param
            modified_files: A set of modified files
            added_files: A set of added files
            old_format_files: A set of old formatted files
        """
        if content:
            for pack, content_item in content.items():
                if (
                    pack.name == API_MODULES_PACK
                ):  # We already handled Api Modules, so we can skip it.
                    continue

                existing_rn_version = self.get_existing_rn(pack.name)
                if (
                    existing_rn_version is None
                ):  # New release notes file already found for the pack
                    raise RuntimeError(
                        f"New release notes file already found for {pack.name}. "
                        f"Please update manually or run `demisto-sdk update-release-notes "
                        f"-i {pack.name}` without specifying the update_type."
                    )

                modified_content = content_item.get("modified", [])
                added_content = content_item.get("new", [])
                old_content = content_item.get("old_format", [])

                pack.create_pack_release_notes(
                    modified_content,
                    added_content,
                    old_content,
                    existing_rn_version,
                    self.update_type,
                    self.pre_release,
                    self.specific_version,
                    self.is_force,
                    self.text,
                    self.is_bc,
                    self.total_updated_packs,
                    self.packs_existing_rn,
                )
        else:
            logger.info(
                "[yellow]No changes that require release notes were detected. If such changes were made, "
                "please commit the changes and rerun the command.[/yellow]"
            )

    def get_existing_rn(self, pack) -> Optional[str]:
        """Gets the existing rn of the pack is exists.

        :param
            pack: The pack to check
        :return
            The existing rn version if exists, otherwise an empty string
            None on error when pack has rn already and update type was given
        """
        if pack not in self.packs_existing_rn:
            return ""

        if self.update_type is None:
            return self.packs_existing_rn[pack]
        else:
            return None
