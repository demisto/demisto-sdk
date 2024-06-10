
from __future__ import annotations
import re
from typing import Iterable, List
import os

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.common.constants import (
    FILE_TYPE_BY_RN_HEADER,
    CUSTOM_CONTENT_FILE_ENDINGS,
    ENTITY_TYPE_TO_DIR,
)
from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_display_name,
)
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

CONTENT_TYPE_SECTION_REGEX = r"^#### ([\w ]+)$\n([\w\W]*?)(?=^#### )|^#### ([\w ]+)$\n([\w\W]*)"
CONTENT_ITEM_SECTION_REGEX = r"^##### (.+)$\n([\w\W]*?)(?=^##### )|^##### (.+)$\n([\w\W]*)|" r"^- (?:New: )?$"

ContentTypes = Pack


class ReleaseNoteInvalidContentNameHeaderValidatorModified(BaseValidator[ContentTypes]):
    error_code = "RN114"
    description = ("Validate the 2nd headers (the content items) are exists in the pack and having the right display"
                   " name.")
    rationale = ("Provide documentation with clear headers for all modifications to make content usage easier."
                 " Validate headers for accuracy.")
    error_message = (
        "The {content_type} '{}' does not exist in the '{}' pack.\n "
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )
    related_field = "release_note"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    expected_git_statuses = [GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(invalid_headers),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_headers := self.validate_release_notes_headers(content_item)  # self.valid_header_name(content_item)
            )
        ]

    def filter_nones(self, ls) -> List:
        """
            Filters out None values from a list or tuple.
        Args:
            ls: (List | Tuple) - This list or tuple to filter.
        Return:
            List filtered from None values.
        """
        return list(filter(lambda x: x, ls))

    def extract_rn_headers(self, markdown_text):
        """
        Extracts headers from Markdown text and returns them in a dictionary with their corresponding header levels.

        Args:
            markdown_text (str): The Markdown text to extract headers from.

        Returns:
            dict: A dictionary containing extracted headers as keys and their corresponding header levels as values.
        """
        headers = {}

        lines = markdown_text.split("\n")
        for line in lines:
            header_item = re.match(r'^#{1,5} ([a-zA-Z0-9]+)$', line)
            header_type = re.match(CONTENT_TYPE_SECTION_REGEX, line)
            # if match:
            #     headers[match.group(2)] = len(match.group(1))
            headers[header_item.group(2)] = len(header_item.group(2)) if header_item else None
        return headers

    def extract_rn_headers_not(self, content_item):
        """
            Extracts the headers from the release notes file.
        Args:
            None.
        Return:
            A dictionary representation of the release notes file that maps content types' headers to their corresponding content items' headers.
        """
        headers = {}
        # Get all sections from the release notes using regex
        rn_sections = re.findall(content_item, CONTENT_TYPE_SECTION_REGEX)
        for section in rn_sections:
            section = self.filter_nones(ls=section)
            content_type = section[0]
            content_type_sections_str = section[1]
            content_type_sections_ls = CONTENT_ITEM_SECTION_REGEX.findall(
                content_type_sections_str
            )
            if not content_type_sections_ls:
                #  Did not find content items headers under content type - might be duo to invalid format.
                #  Will raise error in rn_valid_header_format.
                headers[content_type] = []
            for content_type_section in content_type_sections_ls:
                content_type_section = self.filter_nones(ls=content_type_section)
                if content_type_section:
                    header = content_type_section[0]
                    if headers.get(content_type):
                        headers[content_type].append(header)
                    else:
                        headers[content_type] = [header]
        return headers

    def validate_content_item_header(
            self, content_type: str, content_item
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

        content_items_display_names = set(
            filter(
                lambda x: isinstance(x, str),
                (get_display_name(item) for item in content_type_dir_list),
            )
        )

    def filter_rn_headers(self, headers) -> None:
        """
            Filters out the headers from the release notes file, removing add-ons such as "New" and "**".
        Args:
            headers: (Dict) - The release notes headers to filter, the structure is content type -> headers.(e.g. Integrations -> [header1, header2])
        Return:
            None.
        """
        for content_type, content_items in headers.items():
            content_items = self.filter_nones(ls=content_items)
            headers[content_type] = [
                item.replace("New:", "").strip() for item in content_items
            ]

    def validate_release_notes_headers(self, content_item):
        """
            Validate that the release notes 1st headers are a valid content entity,
            and the 2nd headers are exists in the pack and having the right display name.
        Args:
            None.
        Return:
            True if the release notes headers are valid, False otherwise.
        """
        headers = self.extract_rn_headers(content_item.release_note.file_content)
        validations = []
        self.filter_rn_headers(headers=headers)
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




    #
    # def extract_items(self, content_item):
    #     is_valid = True
    #     entity_type = FILE_TYPE_BY_RN_HEADER.get(content_type, "")
    #
    #     content_type_dir_name = ENTITY_TYPE_TO_DIR.get(entity_type, entity_type)
    #     content_type_path = os.path.join(self.pack_path, content_type_dir_name)
    #
    #     content_type_dir_list = get_files_in_dir(
    #         content_type_path,
    #         CUSTOM_CONTENT_FILE_ENDINGS,
    #         recursive=True,
    #         ignore_test_files=True,
    #     )
    #     if not content_type_dir_list:
    #         print("why")
    #
    #     content_items_display_names = set(
    #         filter(
    #             lambda x: isinstance(x, str),
    #             (get_display_name(item) for item in content_type_dir_list),
    #         )
    #     )
    #     return content_items_display_names
    #
    # def extract_rn_headers(self):
    #     """
    #         Extracts the headers from the release notes file.
    #     Args:
    #         None.
    #     Return:
    #         A dictionary representation of the release notes file that maps content types' headers to their corresponding content items' headers.
    #     """
    #     headers = {}
    #     # Get all sections from the release notes using regex
    #     rn_sections = CONTENT_TYPE_SECTION_REGEX.findall(self.latest_release_notes)
    #     for section in rn_sections:
    #         section = self.filter_nones(ls=section)
    #         content_type = section[0]
    #         content_type_sections_str = section[1]
    #         content_type_sections_ls = CONTENT_ITEM_SECTION_REGEX.findall(
    #             content_type_sections_str
    #         )
    #         if not content_type_sections_ls:
    #             #  Did not find content items headers under content type - might be duo to invalid format.
    #             #  Will raise error in rn_valid_header_format.
    #             headers[content_type] = []
    #         for content_type_section in content_type_sections_ls:
    #             content_type_section = self.filter_nones(ls=content_type_section)
    #             if content_type_section:
    #                 header = content_type_section[0]
    #                 if headers.get(content_type):
    #                     headers[content_type].append(header)
    #                 else:
    #                     headers[content_type] = [header]
    #     return headers
    #
    # def valid_header_name(self, content_item) -> list[str]:
    #
    #     headers = self.extract_headers(content_item.release_note.file_content)
    #     content_items_display_names = self.extract_items(content_item)
    #
    #     for content_item in content_items_display_names:
    #         if content_item in headers:
    #             print("ok")
    #
    #     return []




    

    
