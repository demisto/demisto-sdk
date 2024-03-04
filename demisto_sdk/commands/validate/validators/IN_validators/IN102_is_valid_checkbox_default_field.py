from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import REQUIRED_ALLOWED_PARAMS, ParameterType
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidCheckboxDefaultFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IN102"
    description = "Validate that the checkbox param is configured correctly with required argument set to false."
    rationale = "A checkbox parameter that is required will fail (count as missing) when unchecked, thus forcing the users to always check it, practically turning it into a constant `True` value, rather than a dynamic checkbox."
    error_message = "The following checkbox params required field is set to True: {0}.\nMake sure to change it to False/remove the field."
    fix_message = "Set required field of the following params was set to False: {0}."
    related_field = "configuration"
    is_auto_fixable = True
    misconfigured_checkbox_params_by_integration: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(misconfigured_checkbox_params)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                misconfigured_checkbox_params := self.get_misconfigured_checkbox_params(
                    content_item.params, content_item.name
                )
            )
        ]

    def get_misconfigured_checkbox_params(
        self, params: List[Parameter], integration_name: str
    ):
        self.misconfigured_checkbox_params_by_integration[integration_name] = [
            param.name
            for param in params
            if param.type == ParameterType.BOOLEAN.value
            and param.name not in REQUIRED_ALLOWED_PARAMS
            and param.required
        ]
        return self.misconfigured_checkbox_params_by_integration[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for param in content_item.params:
            if (
                param.name
                in self.misconfigured_checkbox_params_by_integration[content_item.name]
            ):
                param.required = False
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(
                    self.misconfigured_checkbox_params_by_integration[content_item.name]
                )
            ),
            content_object=content_item,
        )
