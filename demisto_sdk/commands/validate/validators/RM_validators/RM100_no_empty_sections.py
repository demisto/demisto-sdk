from __future__ import annotations

import re
from typing import Iterable, List, Union

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

SECTIONS = [
    "Troubleshooting",
    "Use Cases",
    "Known Limitations",
    "Additional Information",
]


class EmptySectionsValidator(BaseValidator[ContentTypes]):
    error_code = "RM100"
    description = """Check that there are no default leftovers such as:
    1. 'FILL IN REQUIRED PERMISSIONS HERE'.
    2. unexplicit version number - such as "version xx of".
    3. Default description belonging to one of the examples integrations`"""
    error_message = (
        "The section/s: {0} is/are empty\nplease elaborate or delete the section.\n"
    )
    related_field = "readme"
    rationale = """Ensure that no default section is left empty with just headings."""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def verify_no_empty_sections(self, content_item: ContentTypes) -> list:
        """Check that if the following headlines exists, they are not empty:
            1. Troubleshooting
            2. Use Cases
            3. Known Limitations
            4. Additional Information
        Returns:
            bool: True If all req ok else False
        """
        empty_sections = []
        for section in SECTIONS:
            found_section = re.findall(
                rf"(## {section}\n*)(-*\s*\n\n?)?(\s*.*)",
                content_item.readme.file_content,
                re.IGNORECASE,
            )
            if not found_section:
                continue

            line_after_headline = str(found_section[0][2])
            # checks if the line after the section's headline is another headline or empty
            if not line_after_headline or line_after_headline.startswith("##"):
                # assuming that a sub headline is part of the section
                if not line_after_headline.startswith("###"):
                    empty_sections.append(section)

        return empty_sections

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(empty_sections)),
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (empty_sections := self.verify_no_empty_sections(content_item))
        ]
