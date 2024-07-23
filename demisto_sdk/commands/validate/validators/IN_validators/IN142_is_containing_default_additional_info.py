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
from demisto_sdk.commands.validate.tools import find_param
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsContainingDefaultAdditionalInfoValidator(BaseValidator[ContentTypes]):
    error_code = "IN142"
    description = "Validate that the integration contain the right additionalinfo fields for the list of params with predefined additionalinfo."
    rationale = "Ensuring the 'additionalinfo' fields are correctly set in an integration's parameters promotes consistency and enhances user understanding of each parameter's purpose and usage."
    error_message = "The integration contains params with missing/malformed additionalinfo fields:\n{0}"
    fix_message = "Fixed the following params additionalinfo fields:ֿ\n{0}"
    related_field = "configuration"
    is_auto_fixable = True
    invalid_params: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        default_additional_info: CaseInsensitiveDict = (
            load_default_additional_info_dict()
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The aditionalinfo field of {key} should be: {val}"
                            for key, val in invalid_params.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
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
        for (
            invalid_param_name,
            invalid_param_valid_additionalinfo,
        ) in self.invalid_params[content_item.name].items():
            if current_param := find_param(content_item.params, invalid_param_name):
                current_param.additionalinfo = invalid_param_valid_additionalinfo
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                "\n".join(
                    [
                        f"The aditionalinfo field of {key} is now: {val}"
                        for key, val in self.invalid_params[content_item.name].items()
                    ]
                )
            ),
            content_object=content_item,
        )
