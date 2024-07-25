from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

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


class IsValidUrlDefaultValueValidator(BaseValidator[ContentTypes]):
    error_code = "IN153"
    description = (
        "Validate that that the url default param starts with https rather than http."
    )
    rationale = "URL parameters should default to 'https' for secure communication. 'http' could expose sensitive data."
    error_message = "The following params have an invalid default value. If possible, replace the http prefix with https: {0}."
    fix_message = (
        "Changed the following params default value to include the https prefix: {0}."
    )
    related_field = "configuration"
    is_auto_fixable = True
    invalid_params: ClassVar[Dict[str, List[str]]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_params)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
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
            if param.defaultvalue
            and isinstance(param.defaultvalue, str)
            and param.defaultvalue.startswith("http:")
        ]
        return self.invalid_params[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for param in content_item.params:
            if param.name in self.invalid_params[content_item.name]:
                param.defaultvalue = f"https{param.defaultvalue[4:]}"  # type: ignore[index]
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.invalid_params[content_item.name])
            ),
            content_object=content_item,
        )
