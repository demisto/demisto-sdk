from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.constants import (
    ALLOWED_HIDDEN_PARAMS,
    MarketplaceVersions,
    ParameterType,
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


class IsHiddenableParamValidator(BaseValidator[ContentTypes]):
    error_code = "IN124"
    description = "Validate that a param is not hidden if it can not be hidden."
    rationale = (
        "Hiding these parameters can lead to confusion and may prevent the integration from working as expected. "
        f"Only the following parameters may be hidden: {ALLOWED_HIDDEN_PARAMS}"
    )
    error_message = (
        "The following fields are hidden and cannot be hidden, please unhide them: {0}."
    )
    fix_message = "Unhiddened the following params {0}."
    related_field = "configuration, hidden"
    is_auto_fixable = True
    invalid_params: ClassVar[Dict[str, list]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_params)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_params := self.get_invalid_hidden_params(
                    content_item.name, content_item.params
                )
            )
        ]

    def get_invalid_hidden_params(
        self, integration_name: str, params: List[Parameter]
    ) -> List[str]:
        """Collect the unhiddenable hidden params.

        Args:
            integration_name (str): The name of the current integration to validate.
            params (List[dict]): The list of the integration params.

        Returns:
            List[str]: The invalid params by name.
        """
        invalid_params = [
            param.name
            for param in params
            if (
                param.hidden in ("true", True)
                or (
                    isinstance(param.hidden, list)
                    and set(param.hidden) == set(MarketplaceVersions)
                )
            )
            and not (
                param.name in ALLOWED_HIDDEN_PARAMS
                or (
                    param.type
                    in (
                        ParameterType.STRING.value,
                        ParameterType.ENCRYPTED.value,
                        ParameterType.TEXT_AREA.value,
                        ParameterType.TEXT_AREA_ENCRYPTED.value,
                    )
                    and self._is_replaced_by_type9(param.display or "", params)
                )
            )
        ]
        self.invalid_params[integration_name] = invalid_params
        return invalid_params

    def _is_replaced_by_type9(self, display_name: str, params: List[Parameter]) -> bool:
        """Validate that there's an existing replacement for a given param display name with type 9.

        Args:
            display_name (str): The display name to search for.
            params (List[Parameter]): The list of the integration parameters.

        Returns:
            bool: True if there's an existing replacement with type 9, otherwise return False.
        """
        for param in params:
            if param.type == ParameterType.AUTH.value and display_name.lower() in (
                (param.display or "").lower(),
                (param.displaypassword or "").lower(),
            ):
                return True
        return False

    def fix(self, content_item: ContentTypes) -> FixResult:
        for invalid_param in self.invalid_params[content_item.name]:
            if current_param := find_param(content_item.params, invalid_param):
                current_param.hidden = False
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.invalid_params[content_item.name])
            ),
            content_object=content_item,
        )
