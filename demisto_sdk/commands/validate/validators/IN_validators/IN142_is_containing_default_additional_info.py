from __future__ import annotations

from typing import ClassVar, Iterable, List

from requests.structures import CaseInsensitiveDict

from demisto_sdk.commands.common.default_additional_info_loader import (
    load_default_additional_info_dict,
)
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


class IsContainingDefaultAdditionalInfoValidator(BaseValidator[ContentTypes]):
    error_code = "IN142"
    description = "Validate that the integration contain the right additionalinfo fields for the list of params with predefined additionalinfo."
    error_message = "The integration contain params with missing/different from the standards additionalinfo fields: {0}"
    fix_message = "Fixed the following params additionalinfo fields: {0}"
    related_field = "configuration"
    is_auto_fixable = True
    invalid_params: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        default_additional_info: CaseInsensitiveDict = (
            load_default_additional_info_dict()
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The aditionalinfo field of {key} should be: {val}."
                            for key, val in invalid_params.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if bool(
                invalid_params := self.get_invalid_params(
                    content_item.params, content_item.name, default_additional_info
                )
            )
        ]

    def get_invalid_params(
        self,
        params: List[Parameter],
        integration_name: str,
        default_additional_info: CaseInsensitiveDict,
    ) -> dict:
        self.invalid_params[integration_name] = {
            param.name: default_additional_info[param.name]
            for param in params
            if param.name in default_additional_info
            and param.additionalinfo != default_additional_info[param.name]
        }
        return self.invalid_params[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for param in content_item.params:
            if param.name in self.invalid_params[content_item]:
                param.additionalinfo = self.invalid_params[content_item][param.name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                "\n".join(
                    [
                        f"The aditionalinfo field of {key} is now: {val}."
                        for key, val in self.invalid_params[content_item].items()
                    ]
                )
            ),
            content_object=content_item,
        )
