from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Set, Tuple, Union

from demisto_sdk.commands.common.constants import (
    CONTENT_ITEM_SECTION_REGEX,
    CONTENT_TYPE_SECTION_REGEX,
    RN_HEADER_BY_FILE_TYPE,
)
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
RN_HEADER_BY_CONTENT_TYPE = {
    ContentType.PLAYBOOK: "Playbooks",
    ContentType.INTEGRATION: "Integrations",
    ContentType.SCRIPT: "Scripts",
    ContentType.INCIDENT_FIELD: "Incident Fields",
    ContentType.INDICATOR_FIELD: "Indicator Fields",
    ContentType.INCIDENT_TYPE: "Incident Types",
    ContentType.CLASSIFIER: "Classifiers",
    ContentType.LAYOUT: "Layouts",
    ContentType.REPORT: "Reports",
    ContentType.WIDGET: "Widgets",
    ContentType.DASHBOARD: "Dashboards",
    ContentType.CONNECTION: "Connections",
    ContentType.MAPPER: "Mappers",
    ContentType.PREPROCESS_RULE: "PreProcess Rules",
    ContentType.GENERIC_DEFINITION: "Objects",
    ContentType.GENERIC_MODULE: "Modules",
    ContentType.GENERIC_TYPE: "Object Types",
    ContentType.GENERIC_FIELD: "Object Fields",
    ContentType.LIST: "Lists",
    ContentType.JOB: "Jobs",
    ContentType.PARSING_RULE: "Parsing Rules",
    ContentType.MODELING_RULE: "Modeling Rules",
    ContentType.CORRELATION_RULE: "Correlation Rules",
    ContentType.XSIAM_DASHBOARD: "XSIAM Dashboards",
    ContentType.XSIAM_REPORT: "XSIAM Reports",
    ContentType.TRIGGER: "Triggers Recommendations",  # https://github.com/demisto/etc/issues/48153#issuecomment-1111988526
    ContentType.WIZARD: "Wizards",
    ContentType.XDRC_TEMPLATE: "XDRC Templates",
    ContentType.LAYOUT_RULE: "Layout Rules",
    ContentType.ASSETS_MODELING_RULE: "Assets Modeling Rules",
    ContentType.CASE_LAYOUT_RULE: "Case Layout Rules",
    ContentType.CASE_FIELD: "Case Fields",
    ContentType.CASE_LAYOUT: "Case Layouts",
}
CONTENT_TYPE_BY_RN_HEADER = {
    header: content_type for content_type, header in RN_HEADER_BY_CONTENT_TYPE.items()
}


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
        "The following invalid headers were found:\n"
        "{content_type_message}{content_item_message}\n"
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )
    related_field = "release_note"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validator_results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.pack_metadata_dict and content_item.pack_metadata_dict.get(
                "hidden"
            ):
                continue
            (
                invalid_headers_content_type,
                invalid_headers_content_item,
            ) = self.validate_release_notes_headers(content_item)
            content_type_message = (
                "Content Types: {}\n".format(", ".join(invalid_headers_content_type))
                if invalid_headers_content_type
                else ""
            )
            content_item_message = (
                "Content Items: {}\n".format(", ".join(invalid_headers_content_item))
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
                    )
                )
        return validator_results

    def remove_none_values(self, ls: Union[List[Any], Tuple[Any, ...]]) -> List[Any]:
        """
        Filters out None values from a list or tuple.

        Args:
            ls (List or Tuple): The list or tuple to filter.

        Returns:
            List: Filtered list with None values removed.
        """
        return list(filter(None, ls))

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
        content_type_section_pattern = re.compile(CONTENT_TYPE_SECTION_REGEX, re.M)
        content_item_section_pattern = re.compile(CONTENT_ITEM_SECTION_REGEX, re.M)

        # Get all sections from the release notes using regex
        rn_sections = content_type_section_pattern.findall(release_note_content)
        for section in rn_sections:
            section = self.remove_none_values(ls=section)
            if not section:
                continue

            content_type = section[0]
            content_type_sections_str = section[1]
            content_type_sections_ls = content_item_section_pattern.findall(
                content_type_sections_str
            )

            if not content_type_sections_ls:
                # Did not find content items headers under content type - might be due to invalid format.
                # Will raise error in rn_valid_header_format.
                headers[content_type] = []

            for content_type_section in content_type_sections_ls:
                content_type_section = self.remove_none_values(ls=content_type_section)
                if content_type_section:
                    header = (
                        content_type_section[0]
                        if ("New: " not in content_type_section[0])
                        else content_type_section[0][5:]
                    )
                    if content_type in headers:
                        headers[content_type].append(header)
                    else:
                        headers[content_type] = [header]

        return headers

    def validate_content_type_header(self, header: str) -> bool:
        """
            Validate that the release notes 1st headers (the content type) are a valid content entity.
        Args:
            content_type: (str) - The content type to validate.(e.g. Integrations, Playbooks, etc.)
        Return:
            True if the content type is valid, False otherwise.
        """
        return header in RN_HEADER_BY_FILE_TYPE.values()

    def validate_content_item_header(
        self,
        headers_to_display_names: Dict[str, List[str]],
        pack_items_by_types: Dict[ContentType, List[ContentItem]],
    ) -> Dict[ContentType, Set[str]]:
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
            content_type = CONTENT_TYPE_BY_RN_HEADER[header]
            pack_display_names = {
                item.display_name for item in pack_items_by_types.get(content_type, [])
            }

            if missing := set(display_names).difference(pack_display_names):
                missing_display_names[content_type] = missing
        return missing_display_names

    def validate_release_notes_headers(
        self, content_item: Pack
    ) -> Tuple[List[str], List[str]]:
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
        headers = self.extract_rn_headers(content_item.release_note.file_content)
        pack_items_by_types = content_item.content_items.items_by_type()
        invalid_content_type: List[str] = [
            header_type
            for header_type in headers.keys()
            if not self.validate_content_type_header(header_type)
        ]
        # removing invalid 1st header types
        valid_headers = {
            key: value
            for key, value in headers.items()
            if key not in invalid_content_type and value
        }
        invalid_content_item: List[str] = [
            value
            for set_value in self.validate_content_item_header(
                valid_headers, pack_items_by_types
            ).values()
            for value in set_value
        ]
        return invalid_content_type, invalid_content_item
