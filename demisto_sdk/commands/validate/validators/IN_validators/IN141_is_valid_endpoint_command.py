from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ENDPOINT_FLEXIBLE_REQUIRED_ARGS
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.tools import find_command
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidEndpointCommandValidator(BaseValidator[ContentTypes]):
    error_code = "IN141"
    description = (
        "Validate that an endpoint command has at least one of the required fields."
    )
    rationale = (
        "Without them, the command may not function properly or may return incomplete or incorrect data. "
        "for more info see https://xsoar.pan.dev/docs/integrations/generic-endpoint-command"
    )
    error_message = f"At least one of these {', '.join(ENDPOINT_FLEXIBLE_REQUIRED_ARGS)} arguments is required for endpoint command."
    related_field = "script.commands"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (command := find_command(content_item.commands, "endpoint"))
            and self.is_invalid_endpoint_command(command)
        ]

    def is_invalid_endpoint_command(self, command: Command) -> bool:
        return not bool(
            {arg.name for arg in command.args}.intersection(
                set(ENDPOINT_FLEXIBLE_REQUIRED_ARGS)
            )
        )
