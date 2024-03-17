from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.constants import ParameterType
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


class IsValidDefaultValueForCheckboxParamValidator(BaseValidator[ContentTypes]):
    error_code = "IN152"
    description = "Validate that the default value of a checkbox param is valid."
    rationale = "Checkbox parameters' default values should be lowercase boolean strings ('true', 'false') for correct interpretation and functionality."
    error_message = "The following checkbox params have invalid defaultvalue: {0}.\nUse a boolean represented as a lowercase string, e.g defaultvalue: 'true'"
    fix_message = "Changed the default values of the following checkbox params: {0}"
    related_field = "configuration"
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
            if bool(
                invalid_params := self.get_invalid_params(
                    content_item.params, content_item.name
                )
            )
        ]

    def get_invalid_params(
        self, params: List[Parameter], integration_name: str
    ) -> List[str]:
        self.invalid_params[integration_name] = [
            param.name
            for param in params
            if param.type == ParameterType.BOOLEAN.value
            and param.defaultvalue is not None
            and not (
                isinstance(param.defaultvalue, str)
                and param.defaultvalue in ["true", "false"]
            )
        ]
        return self.invalid_params[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        changed_params = []
        for param in content_item.params:
            if param.name in self.invalid_params[content_item.name]:
                param.defaultvalue = (
                    "true"
                    if param.defaultvalue is True
                    else "false"
                    if param.defaultvalue is False
                    else None
                )
                changed_params.append(
                    f"param {param.name} default value was changed to {param.defaultvalue}."
                )
        return FixResult(
            validator=self,
            message=self.fix_message.format("\n".join(changed_params)),
            content_object=content_item,
        )
