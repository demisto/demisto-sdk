from __future__ import annotations

import re
from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Script, Integration]

VERSION_NAME_REGEX = r"v([0-9]+)$"


class IsContentItemNameVersionCorrectlyValidator(BaseValidator[ContentTypes]):
    error_code = "BA126"
    description = "Checks if script/integration name is versioned correctly, e.g.: ends with V<number>."
    error_message = (
        "The name {0} of {1} is incorrect , "
        "should be {0}V{2}. e.g: DBotTrainTextClassifierV{3}"
    )
    is_auto_fixable = True
    fix_message = "Updated name {0} to {1}"
    related_field = "name"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            name = content_item.name
            matches = re.findall(VERSION_NAME_REGEX, name)
            if matches:
                version_number = matches[0]
                correct_name = (
                    f"V{matches[0]}"
                    if content_item.content_type == ContentType.SCRIPT
                    else f"v{matches[0]}"
                )
                if not name.endswith(correct_name):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                name,
                                content_item.content_type,
                                version_number,
                                version_number,
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
            content_item.name = content_item.name.replace(
                f"v{matches[0]}", f"V{matches[0]}"
            )
        return FixResult(
            validator=self,
            message=self.fix_message.format(old_name, content_item.name),
            content_object=content_item,
        )
