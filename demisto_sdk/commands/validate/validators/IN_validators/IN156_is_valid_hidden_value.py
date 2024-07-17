from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidHiddenValueValidator(BaseValidator[ContentTypes]):
    error_code = "IN156"
    description = "Validate that the hidden field value contain only valid values."
    rationale = (
        "Incorrect values can cause unexpected behavior or compatibility issues."
    )
    error_message = "The following params contain invalid hidden field values:\n{0}\nThe valid values must be either a boolean, or a list of marketplace values.\n(Possible marketplace values: {1}). Note that this param is not required, and may be omitted."
    related_field = "configuration, hidden"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The param {key} contains the following invalid hidden value: {val}"
                            for key, val in invalid_params.items()
                        ]
                    ),
                    ", ".join(MarketplaceVersions),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_params := self.get_invalid_params(content_item.params))
        ]

    def get_invalid_params(self, params: List[Parameter]) -> dict:
        return {
            param.name: param.hidden
            for param in params
            if param.hidden
            and all(
                [
                    not isinstance(param.hidden, (type(None), bool)),
                    not (
                        isinstance(param.hidden, str)
                        and param.hidden in ["true", "false"]
                    ),
                    not (
                        isinstance(param.hidden, list)
                        and not set(param.hidden).difference(MarketplaceVersions)
                    ),
                ]
            )
        }
