from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidParamDisplayValidator(BaseValidator[ContentTypes]):
    error_code = "IN135"
    description = "Validate that the parameter display name starts with a capital letter and doesn't contain '_'."
    rationale = "Parameter display names should start with a capital letter and not contain underscores for consistency and readability."
    error_message = "The following params are invalid. Integration parameters display field must start with capital letters and can't contain underscores ('_'): {0}."
    fix_message = "The following param displays has been modified: {0}."
    related_field = "display"
    is_auto_fixable = True
    invalid_params: ClassVar[Dict[str, List[str]]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_params)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_params := (
                    self.get_invalid_params(
                        [
                            param.display
                            for param in content_item.params
                            if param.display
                        ],
                        content_item.name,
                    )
                )
            )
        ]

    def get_invalid_params(
        self, params_display: List[str], integration_name: str
    ) -> List[str]:
        """
        This function checks the provided parameters' display names for any that start with a lowercase letter or contain an underscore.
        These are considered invalid as per the naming conventions.

        Args:
            params_display (List[str]): A list of parameter display names to check.
            integration_name (str): The name of the integration the parameters belong to.

        Returns:
            List[str]: A list of invalid parameter display names.
        """
        self.invalid_params[integration_name] = [
            param_display
            for param_display in params_display
            if param_display and param_display[0].islower() or "_" in param_display
        ]
        return self.invalid_params[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        fixed_param_displays = []
        for param in content_item.params:
            if param.display in self.invalid_params[content_item.name]:
                param.display = param.display.capitalize().replace("_", " ")
                fixed_param_displays.append(param.display)
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(
                    [
                        f"{old_val} -> {new_val}"
                        for old_val, new_val in zip(
                            self.invalid_params[content_item.name], fixed_param_displays
                        )
                    ]
                )
            ),
            content_object=content_item,
        )
