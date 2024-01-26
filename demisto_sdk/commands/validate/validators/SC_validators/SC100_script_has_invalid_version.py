from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Script

VERSION_NAME_REGEX = r"v([0-9]+)$"


class ScriptNameIsVersionCorrectlyValidator(BaseValidator[ContentTypes]):
    error_code = "SC100"
    description = (
        "Checks if script name is versioned correctly, e.g.: ends with V<number>."
    )
    error_message = "The name {0} for script is incorrect, it should be {1}."
    is_auto_fixable = True
    fix_message = "Updated name from {0} to {1}"
    related_field = "name"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            name = content_item.name
            matches = re.findall(VERSION_NAME_REGEX, name)
            if matches:
                version_number = matches[0]
                incorrect_version_name = f"v{version_number}"
                correct_version_name = f"V{version_number}"
                if not name.endswith(correct_version_name):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                name,
                                name.replace(
                                    incorrect_version_name, correct_version_name
                                ),
                            ),
                            content_object=content_item,
                        )
                    )

        return invalid_content_items

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        old_name = content_item.name
        matches = re.findall(VERSION_NAME_REGEX, old_name)
        if matches:
            version_number = matches[0]
            incorrect_version_name = f"v{version_number}"
            correct_version_name = f"V{version_number}"
            content_item.name = content_item.name.replace(
                incorrect_version_name, correct_version_name
            )
        return FixResult(
            validator=self,
            message=self.fix_message.format(old_name, content_item.name),
            content_object=content_item,
        )
