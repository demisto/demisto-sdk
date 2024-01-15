from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import COMMON_PARAMS_DISPLAY_NAME
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidProxyAndInsecureValidator(BaseValidator[ContentTypes]):
    error_code = "IN100"
    description = "Validate that the proxy & insecure params are configured correctly."
    error_message = "The following params are invalid:\n{0}"
    fix_message = "Corrected the following params: {0}."
    related_field = "configuration"
    is_auto_fixable = True
    fixed_params: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The {key} param display name should be '{val['display']}', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8."
                            for key, val in self.fixed_params[content_item.name].items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not all(
                [
                    self.is_valid_param(
                        content_item.name, content_item.params, ("insecure", "unsecure")
                    ),
                    self.is_valid_param(
                        content_item.name, content_item.params, ("proxy")
                    ),
                ]
            )
        ]

    def is_valid_param(self, integration_name, params, expected_names):
        current_param = {}
        for param in params:
            if param["name"] in expected_names:
                current_param = param
                break
        if current_param and any(
            [
                current_param.get("display", "")
                != COMMON_PARAMS_DISPLAY_NAME[current_param["name"]],
                current_param.get("defaultvalue", "") not in (False, "false", ""),
                current_param.get("required", False),
                current_param.get("type", "") != 8,
            ]
        ):
            self.fixed_params[integration_name] = self.fixed_params.get(
                integration_name, {}
            )
            self.fixed_params[integration_name][current_param["name"]] = {
                "display": COMMON_PARAMS_DISPLAY_NAME[current_param["name"]],
                "defaultvalue": False,
                "required": False,
                "type": 8,
            }
            return False
        return True

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        for key, val in self.fixed_params[content_item.name].items():
            for param in content_item.params:
                if param["name"] == key:
                    param.update(val)
                    break
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(list(self.fixed_params[content_item.name].keys()))
            ),
            content_object=content_item,
        )
