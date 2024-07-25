from __future__ import annotations

import re
from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration

VERSION_NAME_REGEX = re.compile(r"V([0-9]+)$", re.IGNORECASE)


class IntegrationDisplayNameVersionedCorrectlyValidator(BaseValidator[ContentTypes]):
    error_code = "IN123"
    description = "Checks if integration display name is versioned correctly, e.g.: ends with v<number>."
    rationale = "Integration display names should end with 'v<number>' for version clarity and consistency. "
    error_message = (
        "The display {0} for the integration is incorrect, it should be {1}."
    )
    is_auto_fixable = True
    fix_message = "Updated display from {0} to {1}"
    related_field = "display"
    integration_display_name_to_correct_version: ClassVar[Dict[str, str]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        invalid_content_items = []
        for integration in content_items:
            display_name = integration.display_name
            matches = VERSION_NAME_REGEX.findall(display_name)
            if matches:
                version_number = matches[0]
                incorrect_version_display_name = f"V{version_number}"
                correct_display_name = f"v{version_number}"
                if not display_name.endswith(correct_display_name):
                    correct_display_name = display_name.replace(
                        incorrect_version_display_name, correct_display_name
                    )
                    IntegrationDisplayNameVersionedCorrectlyValidator.integration_display_name_to_correct_version[
                        display_name
                    ] = correct_display_name
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                display_name,
                                correct_display_name,
                            ),
                            content_object=integration,
                        )
                    )

        return invalid_content_items

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        old_display_name = content_item.display_name
        content_item.display_name = self.integration_display_name_to_correct_version[
            old_display_name
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                old_display_name, content_item.display_name
            ),
            content_object=content_item,
        )
