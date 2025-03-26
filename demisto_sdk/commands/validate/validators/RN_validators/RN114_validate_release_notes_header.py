from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set, Tuple

from demisto_sdk.commands.common.constants import PB_RELEASE_NOTES_FORMAT, GitStatuses
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


CONTENT_TYPE_SECTION = re.compile(r"^#### ([\w ]+)$\n([\w\W]*?)(?=^#### |\Z)", re.M)
CONTENT_ITEM_SECTION = re.compile(
    r"^##### (.+)$\n([\w\W]*?)(?=^##### |\Z)|^- (?:New: )?$", re.M
)


class ReleaseNoteHeaderValidator(BaseValidator[ContentTypes]):
    error_code = "RN114"
    description = "Validate the existence of content types in the first-level headers (####) and the content items in second-level headers (#####)."
    rationale = (
        "Providing documentation with accurate information and avoiding confusion."
    )
    error_message = (
        "The following release note headers are invalid:\n"
        "{content_type_message}\n{content_item_message}\n"
    )
    related_field = "release_note"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validator_results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.pack_metadata_dict and content_item.pack_metadata_dict.get(
                "hidden"
            ):
                logger.debug("Content item is marked as hidden. Skipping.")
                continue
            (
                invalid_headers_content_type,
                invalid_headers_content_item,
            ) = self.validate_release_notes_headers(content_item)
            content_type_message = (
                f"Content types: {', '.join(invalid_headers_content_type)}\n"
                if invalid_headers_content_type
                else ""
            )
            content_item_message = (
                f"Content items: {', '.join(invalid_headers_content_item)}\n"
                if invalid_headers_content_item
                else ""
            )
            if invalid_headers_content_type or invalid_headers_content_item:
                validator_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_type_message=content_type_message,
                            content_item_message=content_item_message,
                        ),
                        content_object=content_item,
                        path=content_item.release_note.file_path,
                    )
                )
        return validator_results

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

        # Get all sections from the release notes using regex
        content_type_and_item: List[ContentType] = list(
            filter(None, CONTENT_TYPE_SECTION.findall(release_note_content))
        )
        for section_ in content_type_and_item:
            # Filters out None values from a list or tuple.
            section: list[str] = list(filter(None, section_))
            if not section:
                logger.debug("No content items found under content type section.")
                continue

            # extract content items type, for example: Integrations, Scripts, Playbooks, etc.
            content_type = section[0]

            # extract content items, for example: HelloWorld, HelloWorldScript, HelloWorldPlaybook, etc.
            content_items = section[1]
            content_items_sections_ls = CONTENT_ITEM_SECTION.findall(content_items)

            for content_type_section in content_items_sections_ls:
                # Filters out None values from a list or tuple.
                content_type_section = list(filter(None, content_type_section))
                if content_type_section:
                    logger.debug(
                        f'removing New: " if "New:" in {content_type_section[0]} else "" '
                    )
                    header = (
                        content_type_section[0].rstrip()
                        if ("New: " not in content_type_section[0])
                        else content_type_section[0].removeprefix("New: ")
                    )
                    headers.setdefault(content_type, []).append(header)
        return headers

    def validate_content_type_header(self, header: str) -> bool:
        """
            Validate that the release notes 1st headers (the content type) are a valid content entity.
        Args:
            content_type: (str) - The content type to validate.(e.g. Integrations, Playbooks, etc.)
        Return:
            True if the content type is valid, False otherwise.
        """
        try:
            return (
                ContentType.convert_header_to_content_type(header).as_rn_header
                == header
            )
        except Exception as exception:
            logger.debug(f"Error while converting header to content type {exception=}")
            return False

    def validate_content_item_header(
        self,
        headers_to_display_names: Dict[str, List[str]],
        pack_items_by_types: Dict[ContentType, List[ContentItem]],
    ) -> Dict[str, Set[str]]:
        """
        Validate that the content items' display names match expected values.

        Args:
        headers_to_display_names: A dictionary mapping header names (e.g., Integrations)
            to lists of expected display names for content items.
        pack_items_by_types: A dictionary mapping content types to lists of ContentItem
            instances.

        Returns:
            A dictionary where keys are ContentType and values are sets of invalid display names
            for content items that do not match expected values.
        """
        missing_display_names = {}
        for header, display_names in headers_to_display_names.items():
            logger.debug(f"Validating {header} content items")
            content_type = ContentType.convert_header_to_content_type(header)
            pack_display_names = {
                item.display_name for item in pack_items_by_types.get(content_type, [])
            }
            if missing := set(display_names).difference(pack_display_names):
                missing_display_names[header] = missing
        return missing_display_names

    def validate_release_notes_headers(self, pack: Pack) -> Tuple[List[str], List[str]]:
        """
        Validate that the release notes headers are valid:
        - Validate that the release notes 1st headers are a valid content entity.
        - Validate that the 2nd headers exist in the pack and have the correct display name.

        Args:
            content_item: The content item to validate.

        Returns:
            A tuple containing two lists:
            - List of invalid header types (str or None).
            - List of invalid header content items (str or None).
        """
        headers = self.extract_rn_headers(pack.release_note.file_content)
        remove_pb_headers(headers)
        pack_items_by_types = pack.content_items.items_by_type()
        if case_layout_items := pack_items_by_types.get(ContentType.CASE_LAYOUT, []):
            # case layout using the same header as layout
            pack_items_by_types.setdefault(ContentType.LAYOUT, []).extend(
                case_layout_items
            )
        if not pack_items_by_types:
            return [], []
        invalid_content_type: List[str] = [
            header_type
            for header_type in headers
            if not self.validate_content_type_header(header_type)
        ]
        # removing invalid 1st header types
        valid_headers = {
            key: value
            for key, value in headers.items()
            if key not in invalid_content_type and value
        }

        invalid_content_item: List[str] = [
            f"{header_type}: {', '.join(header_content_item)}"
            for header_type, header_content_item in self.validate_content_item_header(
                valid_headers, pack_items_by_types
            ).items()
        ]
        return invalid_content_type, invalid_content_item


def remove_pb_headers(headers: dict[str, list]):
    if "Playbooks" in headers:
        headers["Playbooks"] = [
            h for h in headers["Playbooks"] if h not in PB_RELEASE_NOTES_FORMAT
        ]
