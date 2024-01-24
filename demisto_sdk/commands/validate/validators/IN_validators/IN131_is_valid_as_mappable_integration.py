from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    GET_MAPPING_FIELDS_COMMAND,
    GET_MAPPING_FIELDS_COMMAND_NAME,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidAsMappableIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN131"
    description = "Validate that the integration is valid as a mappable integration."
    error_message = f"The integration is a mappable integration and is missing the {GET_MAPPING_FIELDS_COMMAND_NAME} command. Please add the command."
    fix_message = (
        f"Added the {GET_MAPPING_FIELDS_COMMAND_NAME} command to the integration."
    )
    related_field = "ismappable, commands"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_mappable
            and not any(
                [
                    command.name == GET_MAPPING_FIELDS_COMMAND_NAME
                    for command in content_item.commands
                ]
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.commands.append(Command(**GET_MAPPING_FIELDS_COMMAND))
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
