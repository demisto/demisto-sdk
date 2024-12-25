import itertools
import os
import re
from typing import List, Tuple, Union

from demisto_sdk.commands.common.constants import (
    CUSTOM_CONTENT_FILE_ENDINGS,
    ENTITY_TYPE_TO_DIR,
    FILE_TYPE_BY_RN_HEADER,
    PACKS_DIR,
    RN_HEADER_BY_FILE_TYPE,
    SKIP_RELEASE_NOTES_FOR_TYPES,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.hook_validations.readme import mdx_server_is_up
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.common.tools import (
    extract_docker_image_from_text,
    find_type,
    get_dict_from_file,
    get_display_name,
    get_files_in_dir,
    get_latest_release_notes_text,
    get_pack_name,
    get_release_notes_file_path,
    get_yaml,
)
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.validate.tools import (
    extract_rn_headers,
    filter_rn_headers_prefix,
)


class ReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        release_notes_file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
    """

    def __init__(
        self,
        release_notes_file_path,
        modified_files=None,
        pack_name=None,
        added_files=None,
        ignored_errors=None,
        json_file_path=None,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self.release_notes_file_path = release_notes_file_path
        self.modified_files = modified_files
        self.added_files = added_files
        self.pack_name = pack_name
        self.pack_path = os.path.join(PACKS_DIR, self.pack_name)
        self.release_notes_path = get_release_notes_file_path(
            self.release_notes_file_path
        )
        self.latest_release_notes = get_latest_release_notes_text(
            self.release_notes_path
        )

    def filter_nones(self, ls: Union[List, Tuple]) -> List:
        """
            Filters out None values from a list or tuple.
        Args:
            ls: (List | Tuple) - This list or tuple to filter.
        Return:
            List filtered from None values.
        """
        return list(filter(lambda x: x, ls))

    @error_codes("RN115")
    def rn_valid_header_format(self, content_type: str, content_items: List) -> bool:
        if not content_items:
            error_message, error_code = Errors.release_notes_invalid_header_format(
                content_type=content_type, pack_name=self.pack_name
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.release_notes_file_path,
                drop_line=True,
            ):
                return False
        return True

    @error_codes("RN113")
    def validate_content_type_header(self, content_type: str) -> bool:
        """
            Validate that the release notes 1st headers (the content type) are a valid content entity.
        Args:
            content_type: (str) - The content type to validate.(e.g. Integrations, Playbooks, etc.)
        Return:
            True if the content type is valid, False otherwise.
        """
        # Get all the content type headers
        rn_valid_headers = RN_HEADER_BY_FILE_TYPE.values()
        if content_type not in rn_valid_headers:
            (
                error_message,
                error_code,
            ) = Errors.release_notes_invalid_content_type_header(
                content_type=content_type, pack_name=self.pack_name
            )
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                return False
        return True

    @error_codes("RN116")
    def validate_first_level_header_exists(self) -> bool:
        """
            Validate that the RN has a first level header.
        Return:
            True if the RN has a first level header, False otherwise.
        """
        first_level_header_index = re.search(
            r"\s#{4}\s", f"\n{self.latest_release_notes}"
        )
        force_header_index = re.search(r"\s#{2}\s", f"\n{self.latest_release_notes}")
        if not (first_level_header_index or force_header_index):
            (
                error_message,
                error_code,
            ) = Errors.first_level_is_header_missing(pack_name=self.pack_name)
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                return False
        return True

    @error_codes("RN113,RN114")
    def validate_content_item_header(
        self, content_type: str, content_items: List
    ) -> bool:
        """
            Validate the 2nd headers (the content items) are exists in the pack and having the right display name.
        Args:
            content_type: (str) - The content type to validate.(e.g. Integrations, Playbooks, etc.)
            content_items: (Dict) - The content items headers to validate.
        Return:
            True if the content item is valid, False otherwise.
        """
        is_valid = True
        entity_type = FILE_TYPE_BY_RN_HEADER.get(content_type, "")

        content_type_dir_name = ENTITY_TYPE_TO_DIR.get(entity_type, entity_type)
        content_type_path = os.path.join(self.pack_path, content_type_dir_name)

        content_type_dir_list = get_files_in_dir(
            content_type_path,
            CUSTOM_CONTENT_FILE_ENDINGS,
            recursive=True,
            ignore_test_files=True,
        )
        if not content_type_dir_list:
            (
                error_message,
                error_code,
            ) = Errors.release_notes_invalid_content_type_header(
                content_type=content_type, pack_name=self.pack_name
            )
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                is_valid = False

        content_items_display_names = set(
            filter(
                lambda x: isinstance(x, str),
                (get_display_name(item) for item in content_type_dir_list),
            )
        )

        for header in set(content_items).difference(content_items_display_names):
            (
                error_message,
                error_code,
            ) = Errors.release_notes_invalid_content_name_header(
                content_name_header=header,
                pack_name=self.pack_name,
                content_type=entity_type,
            )
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                is_valid = False
        return is_valid

    @error_codes("RN107")
    def are_release_notes_complete(self):
        is_valid = True
        modified_added_files = itertools.chain.from_iterable(
            (self.added_files or [], self.modified_files or [])
        )
        if modified_added_files:
            for file in modified_added_files:
                # renamed files will appear in the modified list as a tuple: (old path, new path)
                if isinstance(file, tuple):
                    file = file[1]
                checked_file_pack_name = get_pack_name(file)

                if find_type(file) in SKIP_RELEASE_NOTES_FOR_TYPES:
                    continue

                elif (
                    checked_file_pack_name and checked_file_pack_name == self.pack_name
                ):
                    try:
                        _dict, file_type = get_dict_from_file(file)
                        if _dict.get("issilent"):
                            continue
                    except Exception:
                        pass
                    # Refer image and description file paths to the corresponding yml files
                    file = UpdateRN.change_image_or_desc_file_path(file)
                    update_rn_util = UpdateRN(
                        pack_path=self.pack_path,
                        modified_files_in_pack=set(),
                        update_type=None,
                        added_files=set(),
                        pack=self.pack_name,
                    )
                    (
                        file_name,
                        file_type,
                    ) = update_rn_util.get_changed_file_name_and_type(file)
                    if file_name and file_type and file_type in RN_HEADER_BY_FILE_TYPE:
                        if (
                            RN_HEADER_BY_FILE_TYPE[file_type]
                            not in self.latest_release_notes
                        ) or (file_name not in self.latest_release_notes):
                            (
                                error_message,
                                error_code,
                            ) = Errors.missing_release_notes_entry(
                                file_type, self.pack_name, file_name
                            )
                            if self.handle_error(
                                error_message, error_code, self.release_notes_file_path
                            ):
                                is_valid = False
        return is_valid

    @error_codes("RN104,RN103")
    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.strip_exclusion_tag(self.latest_release_notes)
        if len(release_notes_comments) == 0:
            error_message, error_code = Errors.release_notes_file_empty()
            if self.handle_error(
                error_message, error_code, file_path=self.release_notes_file_path
            ):
                return False
        elif any(
            note in release_notes_comments
            for note in ["%%UPDATE_RN%%", "%%XSIAM_VERSION%%"]
        ):
            error_message, error_code = Errors.release_notes_not_finished()
            if self.handle_error(
                error_message, error_code, file_path=self.release_notes_file_path
            ):
                return False
        return True

    @error_codes("RN111")
    def is_docker_image_same_as_yml(self) -> bool:
        """
        Iterates on all modified yaml files,
        checking if the yaml is related to one of the sections in the RN and if there's a docker-image version update mentioned in the RN.
        If so, make sure the versions match.

        Return:
            True if for all the modified yaml files, if there was a change in the docker image in the RN, it's the same version as the yaml.
            Otherwise, return False and a release_notes_docker_image_not_match_yaml Error
        """
        release_notes_categories = self.get_categories_from_rn(
            "\n" + self.latest_release_notes
        )
        # renamed files will appear in the modified list as a tuple: (old path, new path)
        modified_files_list = [
            file[1] if isinstance(file, tuple) else file
            for file in (self.modified_files or [])
        ]
        modified_yml_list = [
            file for file in modified_files_list if file.endswith(".yml")
        ]
        rn_file_name = self.release_notes_file_path[
            self.release_notes_file_path.rindex("/") + 1 :
        ]
        error_list = []
        for type, field in zip(["Integrations", "Scripts"], ["display", "name"]):
            if type in release_notes_categories:
                splited_release_notes_entities = self.get_entities_from_category(
                    f"\n{release_notes_categories.get(type)}"
                )
                for modified_yml_file in modified_yml_list:
                    modified_yml_dict = get_yaml(modified_yml_file) or {}
                    if modified_yml_dict.get(field) in splited_release_notes_entities:
                        entity_conent = (
                            splited_release_notes_entities.get(
                                modified_yml_dict.get(field, {}), ""
                            )
                            + "\n"
                        )
                        docker_version = self.get_docker_version_from_rn(entity_conent)
                        yml_docker_version = (
                            modified_yml_dict.get("dockerimage")
                            if type == "Scripts"
                            else modified_yml_dict.get("script", {}).get(
                                "dockerimage", ""
                            )
                        )
                        if (
                            docker_version
                            and yml_docker_version
                            and yml_docker_version != docker_version
                        ):
                            error_list.append(
                                {
                                    "name": modified_yml_dict.get(field),
                                    "rn_version": docker_version,
                                    "yml_version": yml_docker_version,
                                }
                            )
        if len(error_list) > 0:
            (
                error_message,
                error_code,
            ) = Errors.release_notes_docker_image_not_match_yaml(
                rn_file_name, error_list, self.pack_path
            )
            if self.handle_error(
                error_message, error_code, file_path=self.release_notes_file_path
            ):
                return False

        return True

    @error_codes("RN112")
    def validate_json_when_breaking_changes(self) -> bool:
        """
        In case of a breaking change in the release note, ensure the existence of a proper json file.
        """
        is_valid = True
        if "breaking change" in self.latest_release_notes.lower():
            json_path = self.release_notes_file_path[:-2] + "json"
            error_message, error_code = Errors.release_notes_bc_json_file_missing(
                json_path
            )
            try:
                json_file_content = get_dict_from_file(path=json_path)[
                    0
                ]  # extract only the dictionary
                if (
                    "breakingChanges" not in json_file_content
                    or not json_file_content.get("breakingChanges")
                ):
                    if self.handle_error(
                        error_message, error_code, self.release_notes_file_path
                    ):
                        is_valid = False
            except FileNotFoundError:
                if self.handle_error(
                    error_message, error_code, self.release_notes_file_path
                ):
                    is_valid = False
        return is_valid

    @error_codes("RN113")
    def has_no_markdown_lint_errors(self):
        """
        Will check if the readme has markdownlint.
        Returns: a boolean to fail the validations according to markdownlint

        """
        if mdx_server_is_up():
            markdown_response = run_markdownlint(self.latest_release_notes)
            if markdown_response.has_errors:
                error_message, error_code = Errors.release_notes_lint_errors(
                    self.release_notes_file_path, markdown_response.validations
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.release_notes_file_path
                ):
                    return False

        return True

    def validate_release_notes_headers(self):
        """
            Validate that the release notes 1st headers are a valid content entity,
            and the 2nd headers are exists in the pack and having the right display name.
        Args:
            None.
        Return:
            True if the release notes headers are valid, False otherwise.
        """
        headers = extract_rn_headers(self.latest_release_notes)
        validations = [self.validate_first_level_header_exists()]
        filter_rn_headers_prefix(headers=headers)
        for content_type, content_items in headers.items():
            validations.append(
                self.rn_valid_header_format(
                    content_type=content_type, content_items=content_items
                )
            )
            validations.append(
                self.validate_content_type_header(content_type=content_type)
            )
            validations.append(
                self.validate_content_item_header(
                    content_type=content_type, content_items=content_items
                )
            )
        return all(validations)

    @staticmethod
    def get_docker_version_from_rn(section: str) -> str:
        """
        Extract the docker image version from the relevant section in the RN if mentioned.
        Args:
            section (str): the section to search its docker image version note
        Return:
            (str): The docker image version if exists, otherwise, return None.
        """
        updates_list = section.split("\n")
        for update in updates_list:
            if "Docker image" in update and "demisto/" in update:
                return extract_docker_image_from_text(update)
        return ""

    @staticmethod
    def get_information_from_rn(rn: str, splitter: str) -> dict:
        """
            Extract the various categories from the release note according to the splitter
            rn : the release notes
            splitter: a string to split by
        Return:
            dict. dictionary where each entry is the category name in the release notes
            and its value is the change for that category.
        """
        splitted_text = rn.split(splitter)
        splitted_categories_dict = {}
        for category in splitted_text:
            if category:
                splitted_categories_dict[category[0 : category.index("\n")]] = category[
                    category.index("\n") + 1 :
                ]
        return splitted_categories_dict

    def get_categories_from_rn(self, rn: str) -> dict:
        return self.get_information_from_rn(rn, "\n#### ")

    def get_entities_from_category(self, rn: str) -> dict:
        return self.get_information_from_rn(rn, "\n##### ")

    @staticmethod
    def strip_exclusion_tag(release_notes_comments):
        """
        Strips the exclusion tag (<!-- -->) from the release notes since release notes should never
        be empty as this is poor user experience.
        Return:
            str. Cleaned notes with tags and contained notes removed.
        """
        return re.sub(r"<\!--.*?-->", "", release_notes_comments, flags=re.DOTALL)

    def is_file_valid(self):
        """Checks if given file is valid.

        Return:
            bool. True if file's release notes are valid, False otherwise.
        """
        validations = [
            self.has_release_notes_been_filled_out(),
            self.are_release_notes_complete(),
            self.is_docker_image_same_as_yml(),
            self.validate_json_when_breaking_changes(),
            # self.has_no_markdown_lint_errors(),
            self.validate_release_notes_headers(),
            self.validate_no_disallowed_terms_in_customer_facing_docs(
                file_content=self.latest_release_notes,
                file_path=self.release_notes_file_path,
            ),
        ]
        return all(validations)
