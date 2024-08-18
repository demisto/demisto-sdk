from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.constants import XSOAR_SUPPORT
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


class IsContainingFromLicenseInParamsValidator(BaseValidator[ContentTypes]):
    error_code = "IN146"
    description = "Validate that there's no fromlicense param field in non Xsoar supported integration"
    rationale = "The `fromlicense` param is intended for XSOAR-supported integrations, as they rely on values coming stored in the platform."
    error_message = 'The following parameters contain the "fromlicense" field: {0}. The field is not allowed for contributors, please remove it.'
    fix_message = "Removed the fromlicense field from the following parameters: {0}."
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
            if content_item.support != XSOAR_SUPPORT
            and (
                invalid_params := self.get_invalid_params(
                    content_item.params, content_item.name
                )
            )
        ]

    def get_invalid_params(
        self, params: List[Parameter], integration_name: str
    ) -> List[str]:
        self.invalid_params[integration_name] = [
            param.name for param in params if param.fromlicense
        ]
        return self.invalid_params[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for param in content_item.params:
            if param.name in self.invalid_params[content_item.name]:
                param.fromlicense = None
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.invalid_params[content_item.name])
            ),
            content_object=content_item,
        )
