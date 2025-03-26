from __future__ import annotations

import re
from typing import Iterable, List, Optional, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]

USER_FILL_SECTIONS = [
    "FILL IN REQUIRED PERMISSIONS HERE",
    "version xx",
    "%%UPDATE%%",
]
PACKS_TO_IGNORE = ["HelloWorld", "HelloWorldPremium"]
DEFAULT_SENTENCES = ["getting started and learn how to build an integration"]


class NoDefaultSectionsLeftReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM115"
    description = """Check that there are no default leftovers such as:
    1. 'FILL IN REQUIRED PERMISSIONS HERE'.
    2. unexplicit version number - such as "version xx of".
    3. Default description belonging to one of the examples integrations"""
    error_message = "The following default sentences {0} still exist in the readme, please replace with a suitable info."
    related_field = "readme"
    rationale = "Ensure no default auto generated sections remain empty. For better documentation standards and quality."
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def verify_no_default_sections_left(self, content_item: ContentTypes) -> list:
        """Check that there are no default leftovers"""
        sections = []
        sections = self._find_section_in_text(
            content_item, USER_FILL_SECTIONS
        ) + self._find_section_in_text(content_item, DEFAULT_SENTENCES, PACKS_TO_IGNORE)
        return sections

    def _find_section_in_text(
        self,
        content_item: ContentTypes,
        sections_list: List[str],
        ignore_packs: Optional[List[str]] = None,
    ) -> list:
        """
        Find if sections from the sections list appear in the readme content and returns an error message.
        Arguments:
            sections_list (List[str]) - list of strings, each string is a section to find in the text
            ignore_packs (List[str]) - List of packs and integration names to be ignored
        Returns:
            An error message with the relevant sections.
        """
        found_sections: list = []
        current_pack_name = content_item.pack_name
        if ignore_packs and current_pack_name in ignore_packs:
            return found_sections

        for section in sections_list:
            required_section = re.findall(
                rf"{section}", content_item.readme.file_content, re.IGNORECASE
            )
            if required_section:
                found_sections.append(section)

        return found_sections

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join([f'"{section}"' for section in sections])
                ),
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (sections := (self.verify_no_default_sections_left(content_item)))
        ]
