from __future__ import annotations

import re
from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Script

VERSION_NAME_REGEX = re.compile(r"V([0-9]+)$", re.IGNORECASE)


class ScriptNameIsVersionedCorrectlyValidator(BaseValidator[ContentTypes]):
    error_code = "SC100"
    description = (
        "Checks if script name is versioned correctly, e.g.: ends with V<number>."
    )
    rationale = "This standardization ensures consistency across content items."
    error_message = "The name {0} for the script is incorrect, it should be {1}."
    is_auto_fixable = True
    fix_message = "Updated name from {0} to {1}"
    related_field = "name"
    script_name_to_correct_version: ClassVar[Dict[str, str]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        invalid_content_items = []
        for script in content_items:
            name = script.name
            matches = VERSION_NAME_REGEX.findall(name)
            if matches:
                version_number = matches[0]
                incorrect_version_name = f"v{version_number}"
                correct_version_name = f"V{version_number}"
                if not name.endswith(correct_version_name):
                    correct_version_name = name.replace(
                        incorrect_version_name, correct_version_name
                    )
                    ScriptNameIsVersionedCorrectlyValidator.script_name_to_correct_version[
                        name
                    ] = correct_version_name
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                name,
                                correct_version_name,
                            ),
                            content_object=script,
                        )
                    )

        return invalid_content_items

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        old_name = content_item.name
        content_item.name = self.script_name_to_correct_version[old_name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(old_name, content_item.name),
            content_object=content_item,
        )
