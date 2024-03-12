from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses, ParameterType
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingDisplayFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IN118"
    description = "Validate that the integration parameter has a display field if it's not of type 17."
    rationale = "Integration parameters should have a 'display' field for clear user understanding, except for type 17 parameters."
    error_message = "The following params doesn't have a display field, please make sure to add one: {0}."
    related_field = "display, displaypassowrd"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_params)),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_params := self.get_invalid_params(content_item.params))
        ]

    def get_invalid_params(self, params: List[Parameter]) -> List[str]:
        """Validate that all the relevant params have a display name.

        Args:
            params (List[dict]): The integration params.

        Returns:
            List[str]: The list of the names of the params that are not valid.
        """
        return [
            param.name
            for param in params
            if param.type != ParameterType.EXPIRATION_FIELD.value
            and not param.hidden
            and not param.display
            and not param.displaypassword
            and param.name not in ("feedExpirationPolicy", "feedExpirationInterval")
        ]
