from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsCommandStartsWithDigitValidator(BaseValidator[ContentTypes]):
    error_code = "BA128"
    description = "Command name cannot start with a digit"
    rationale = "Not supported by the platform"
    error_message = "Command name cannot start with a digit"
    related_field = "name"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []

        for content_item in content_items:
            is_valid = True

            if isinstance(content_item, Integration) and any(
                (command.name and command.name[0].isdigit())
                for command in content_item.commands
            ):
                is_valid = False

            elif isinstance(content_item, Script) and content_item.name[0].isdigit():
                is_valid = False

            if not is_valid:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message,
                        content_object=content_item,
                    )
                )

        return validation_results
