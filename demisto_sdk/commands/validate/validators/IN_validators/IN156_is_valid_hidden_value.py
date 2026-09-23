from __future__ import annotations

from typing import Any, Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import (
    Command,
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidHiddenValueValidator(BaseValidator[ContentTypes]):
    error_code = "IN156"
    description = "Validate that the hidden field value contain only valid values."
    rationale = (
        "Incorrect values can cause unexpected behavior or compatibility issues."
    )
    error_message = "The following params contain invalid hidden field values:\n{0}\nThe valid values must be either a boolean, or a list of marketplace values.\n(Possible marketplace values: {1}). Note that this param is not required, and may be omitted."
    related_field = "configuration, hidden"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_params = self.get_invalid_params(content_item.params)
            invalid_commands = self.get_invalid_commands(content_item.commands)
            if not invalid_params and not invalid_commands:
                continue

            lines = [
                f"The param {key} contains the following invalid hidden value: {val}"
                for key, val in invalid_params.items()
            ] + [
                f"The command {key} contains the following invalid hidden value: {val}"
                for key, val in invalid_commands.items()
            ]
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        "\n".join(lines),
                        ", ".join(MarketplaceVersions),
                    ),
                    content_object=content_item,
                )
            )
        return results

    @staticmethod
    def _is_invalid_hidden_value(hidden: Any) -> bool:
        """Return True if the given `hidden` value is neither a bool/None nor a
        list of valid marketplace names (or the strings "true"/"false")."""
        if not hidden:
            return False
        return all(
            [
                not isinstance(hidden, (type(None), bool)),
                not (isinstance(hidden, str) and hidden in ["true", "false"]),
                not (
                    isinstance(hidden, list)
                    and not set(hidden).difference(MarketplaceVersions)
                ),
            ]
        )

    def get_invalid_params(self, params: List[Parameter]) -> dict:
        return {
            param.name: param.hidden
            for param in params
            if self._is_invalid_hidden_value(param.hidden)
        }

    def get_invalid_commands(self, commands: List[Command]) -> dict:
        return {
            command.name: command.hidden
            for command in commands
            if self._is_invalid_hidden_value(command.hidden)
        }
