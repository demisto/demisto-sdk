from __future__ import annotations

from typing import ClassVar, Iterable, List, Tuple, Union

from demisto_sdk.commands.common.constants import (
    COMMON_PARAMS_DISPLAY_NAME,
    ParameterType,
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


class IsValidProxyAndInsecureValidator(BaseValidator[ContentTypes]):
    error_code = "IN100"
    description = "Validate that the proxy & insecure params are configured correctly."
    rationale = "The 'proxy' and 'insecure' parameters in an integration are builtin platform parameters"
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
                            f"The {key} param display name should be '{val['display']}', the 'defaultvalue' field should be 'false', the 'required' field should be 'False', and the 'type' field should be 8."
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

    def is_valid_param(
        self,
        integration_name: str,
        params: List[Parameter],
        expected_names: Union[str, Tuple],
    ) -> bool:
        current_param = None
        for param in params:
            if param.name in expected_names:
                current_param = param
                break
        if current_param and any(
            [
                current_param.display != COMMON_PARAMS_DISPLAY_NAME[current_param.name],
                current_param.defaultvalue not in (False, "false", None),
                current_param.required,
                current_param.type != ParameterType.BOOLEAN.value,
            ]
        ):
            self.fixed_params[integration_name] = self.fixed_params.get(
                integration_name, {}
            )
            self.fixed_params[integration_name][current_param.name] = {
                "display": COMMON_PARAMS_DISPLAY_NAME[current_param.name],
                "defaultvalue": False,
                "required": False,
                "type": ParameterType.BOOLEAN.value,
            }
            return False
        return True

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        for key, val in self.fixed_params[content_item.name].items():
            for param in content_item.params:
                if param.name == key:
                    param.display = val["display"]
                    param.defaultvalue = "false"
                    param.required = False
                    param.type = ParameterType.BOOLEAN.value
                    break
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(list(self.fixed_params[content_item.name].keys()))
            ),
            content_object=content_item,
        )
