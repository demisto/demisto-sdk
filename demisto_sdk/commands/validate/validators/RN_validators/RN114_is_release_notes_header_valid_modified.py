
from __future__ import annotations
import re
from typing import Iterable, List, Dict, Union, Tuple
import os

# from demisto_sdk.commands.common.constants import (
#     CUSTOM_CONTENT_FILE_ENDINGS,
#     ENTITY_TYPE_TO_DIR,
#     FILE_TYPE_BY_RN_HEADER,
#     PACKS_DIR,
#     RN_HEADER_BY_FILE_TYPE,
#     SKIP_RELEASE_NOTES_FOR_TYPES,
# )
from demisto_sdk.commands.common.constants import (
    GitStatuses,
    RN_HEADER_BY_FILE_TYPE,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.common.constants import (
    FILE_TYPE_BY_RN_HEADER,
    CUSTOM_CONTENT_FILE_ENDINGS,
    ENTITY_TYPE_TO_DIR,
    MARKDOWN_HEADER
)
from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_display_name,
)
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)


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

    def extract_headers(self, markdown_content):
        headers_map = {}
        current_content_type = None

        lines = markdown_content.split('\n')

        for line in lines:
            content_type_match = re.match(r'^####\s+(.*)$', line)
            content_item_match = re.match(r'^#####\s+(.*)$', line)

            if content_type_match:
                current_content_type = content_type_match.group(1)
                headers_map[current_content_type] = []
            elif content_item_match and current_content_type:
                headers_map[current_content_type].append(content_item_match.group(1))

        return headers_map




        # Iterate over each line
        for line in lines:
            # Check if the line matches the header pattern
            match = re.match(MARKDOWN_HEADER, line)
            if match:
                # Extract the header level and header text
                header_level = len(match.group(1))
                header_text = match.group(2).strip()

                # Map the header to its corresponding content type
                if header_level == 4:
                    content_type = header_text
                    headers_map[content_type] = []
                elif header_level == 5:
                    content_type_headers = headers_map.get(content_type)
                    if content_type_headers is not None:
                        content_type_headers.append(header_text)
        return headers_map

    def rn_valid_header_format(self, content_type: str) -> str:
        rn_valid_headers = RN_HEADER_BY_FILE_TYPE.values()
        if content_type not in rn_valid_headers:
            return f"The content type {content_type} isn't valid"
        return ''

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
            return False
        return True

    def validate_content_item_header(
        self, content_type: str, content_items: List, content_item
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
        content_type_path = os.path.join(content_item.pack_path, content_type_dir_name)

        content_type_dir_list = get_files_in_dir(
            content_type_path,
            CUSTOM_CONTENT_FILE_ENDINGS,
            recursive=True,
            ignore_test_files=True,
        )
        if not content_type_dir_list:
            is_valid = False

        content_items_display_names = set(
            filter(
                lambda x: isinstance(x, str),
                (get_display_name(item) for item in content_type_dir_list),
            )
        )

        for header in set(content_items).difference(content_items_display_names):
             is_valid = False
        return is_valid

    def validate_release_notes_headers(self, content_item):
        """
        Returns:

            Validate that the release notes 1st headers are a valid content entity,
            and the 2nd headers are exists in the pack and having the right display name.
        Args:
            None.
        Return:
            True if the release notes headers are valid, False otherwise.
        """
        errors = ''
        headers = self.extract_headers(content_item.release_note.file_content)
        for content_type, content_items in headers.items():
            # if invalid_header_type_format := not self.validate_content_type_header(content_type=content_type):
            #     errors += invalid_header_type_format

            if not self.validate_content_item_header(content_type=content_type, content_items=content_items,
                                                     content_item=content_item):
                errors += "blabla"
        return errors
