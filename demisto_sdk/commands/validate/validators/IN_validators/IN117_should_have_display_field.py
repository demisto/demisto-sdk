from __future__ import annotations

from typing import ClassVar, Iterable, List

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


class ShouldHaveDisplayFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IN117"
    description = (
        "Validate that type 17 configuration params doesn't include the display field."
    )
    rationale = "The display name is handle by the platform."
    error_message = "The following params are expiration fields and therefore can't have a 'display' field. Make sure to remove the field for the following: {0}."
    fix_message = "Removed display field for the following params: {0}."
    related_field = "display, type"
    is_auto_fixable = True
    invalid_params: ClassVar[dict] = {}

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
        """Validate that all the params are not of type 17 and include a display field.

        Args:
            params (List[dict]): The integration params.
            integration_name (str): The name of the integration.

        Returns:
            List[str]: The list of the names of the params that are not valid.
        """
        self.invalid_params[integration_name] = [
            param.name
            for param in params
            if param.type == ParameterType.EXPIRATION_FIELD.value and param.display
        ]
        return self.invalid_params.get(integration_name, [])

    def fix(self, content_item: ContentTypes) -> FixResult:
        invalid_params = self.invalid_params[content_item.name]
        for param in content_item.params:
            if param.name in invalid_params:
                param.display = None
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(invalid_params)),
            content_object=content_item,
        )
