from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Set, Tuple, Union

from demisto_sdk.commands.common.constants import (
    CONTENT_ITEM_SECTION_REGEX,
    CONTENT_TYPE_SECTION_REGEX,
    CUSTOM_CONTENT_FILE_ENDINGS,
    ENTITY_TYPE_TO_DIR,
    FILE_TYPE_BY_RN_HEADER,
    RN_HEADER_BY_FILE_TYPE,
)
from demisto_sdk.commands.common.tools import (
    get_display_name,
    get_files_in_dir,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class ReleaseNoteHeaderValidator(BaseValidator[ContentTypes]):
    error_code = "RN114"
    description = (
        "Validate the 2nd headers (the content items) are exists in the pack and having the right display"
        " name."
    )
    rationale = (
        "Provide documentation with clear headers for all modifications to make content usage easier."
        " Validate headers for accuracy."
    )
    error_message = (
        "The invalid header(s) were found.\n{content_type}\n{content_item}\n"
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )
    related_field = "release_note"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_type=f"The content header(s) type are invalid:"
                    f' {", ".join(invalid_headers[0])}',
                    content_item=f"those are the items:"
                    f' {", ".join(invalid_headers[1])}',
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_headers := self.validate_release_notes_headers(content_item))
        ]

    def remove_none_values(self, ls: Union[List[Any], Tuple[Any, ...]]) -> List[Any]:
        """
        Filters out None values from a list or tuple.

        Args:
            ls (List or Tuple): The list or tuple to filter.

        Returns:
            List: Filtered list with None values removed.
        """
        return list(filter(lambda x: x, ls))

    def extract_rn_headers(self, release_note_content: str) -> Dict[str, List[str]]:
        """
        Extracts the headers from the release notes file.

        Args:
            release_note_content (str): Content of the release notes file.

        Return:
            Dict[str, List[str]]: A dictionary representation of the release notes file that maps
                                  content types' headers to their corresponding content items' headers.
        """
        headers: Dict[str, List[str]] = {}
        content_type_section = re.compile(CONTENT_TYPE_SECTION_REGEX, re.M)
        content_item_section = re.compile(CONTENT_ITEM_SECTION_REGEX, re.M)

        # Get all sections from the release notes using regex
        rn_sections = content_type_section.findall(release_note_content)
        for section in rn_sections:
            section = self.remove_none_values(ls=section)
            if not section:
                continue

            content_type = section[0]
            content_type_sections_str = section[1]
            content_type_sections_ls = content_item_section.findall(
                content_type_sections_str
            )

            if not content_type_sections_ls:
                # Did not find content items headers under content type - might be due to invalid format.
                # Will raise error in rn_valid_header_format.
                headers[content_type] = []

            for content_type_section in content_type_sections_ls:
                content_type_section = self.remove_none_values(ls=content_type_section)
                if content_type_section:
                    header = content_type_section[0]
                    if content_type in headers:
                        headers[content_type].append(header)
                    else:
                        headers[content_type] = [header]

        return headers

    def validate_content_type_header(self, content_type: str) -> bool:
        """
            Validate that the release notes 1st headers (the content type) are a valid content entity.
        Args:
            content_type: (str) - The content type to validate.(e.g. Integrations, Playbooks, etc.)
        Return:
            True if the content type is valid, False otherwise.
        """
        rn_valid_headers = RN_HEADER_BY_FILE_TYPE.values()
        return True if content_type in rn_valid_headers else False

    def validate_content_item_header(
        self, header_content_type: str, header_content_items: List[str], content_item
    ) -> Set[str]:
        """
        Validate that the content items' display names match expected values.

        Args:
            header_content_type: (str) - The type of content to validate (e.g., Integrations, Playbooks, etc.).
            header_content_items: (List) - List of expected display names for content items.
            content_item: Placeholder for the content item.

        Returns:
            Set: Invalid content items' display names.
        """
        entity_type = FILE_TYPE_BY_RN_HEADER.get(header_content_type, "")

        content_type_dir_name = ENTITY_TYPE_TO_DIR.get(entity_type, entity_type)
        content_type_path = str(os.path.join(content_item.path, content_type_dir_name))

        content_type_dir_list = get_files_in_dir(
            content_type_path,
            CUSTOM_CONTENT_FILE_ENDINGS,
            recursive=True,
            ignore_test_files=True,
        )
        if not content_type_dir_list:
            return set()
        existing_display_names = {
            get_display_name(item)
            for item in content_type_dir_list
            if isinstance(item, str)
        }
        expected_display_names = set(header_content_items)
        invalid_display_names = expected_display_names.difference(
            existing_display_names
        )
        return invalid_display_names

    def validate_release_notes_headers(self, content_item):
        """
        Validate that the release notes headers are valid:
        - Validate that the release notes 1st headers are a valid content entity.
        - Validate that the 2nd headers exist in the pack and have the correct display name.

        Args:
            content_item: The content item to validate.

        Returns:
            str: Error if headers are invalid, or an empty string if all headers are valid.
        """
        invalid_headers = []
        headers = self.extract_rn_headers(content_item.release_note.file_content)
        invalid_headers_type = [
            header_type
            for header_type in headers.keys()
            if not self.validate_content_type_header(header_type)
        ]
        if invalid_headers_type:
            invalid_headers.append(invalid_headers_type)
        invalid_headers_content_item = []
        for header_type, header_content_items in headers.items():
            invalid_items = self.validate_content_item_header(
                header_type, header_content_items, content_item
            )
            if invalid_items:
                invalid_headers_content_item.extend(invalid_items)
        if invalid_headers_content_item:
            invalid_headers.append(invalid_headers_content_item)
        return invalid_headers
