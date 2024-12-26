from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsCommandOrScriptNameStartsWithDigitValidator(BaseValidator[ContentTypes]):
    error_code = "BA128"
    description = "Ensure that integration command names and script names cannot start with a digit."
    rationale = "Ensure we don't add commands which are not supported by the platform."
    error_message = "The following {0} names start with a digit: {1}"
    related_field = "name"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []

        for content_item in content_items:
            content_type = ""
            invalid_command_names = []

            if isinstance(content_item, Integration):
                content_type = "integration command"
                invalid_command_names.extend(
                    [
                        command.name
                        for command in content_item.commands
                        if command.name and command.name[0].isdigit()
                    ]
                )

            elif isinstance(content_item, Script) and content_item.name[0].isdigit():
                content_type = "script"
                invalid_command_names.append(content_item.name)

            if invalid_command_names:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_type,
                            ", ".join(invalid_command_names),
                        ),
                        content_object=content_item,
                    )
                )

        return validation_results
