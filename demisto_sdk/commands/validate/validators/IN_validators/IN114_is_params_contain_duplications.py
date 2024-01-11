from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsParamsContainDuplicationsValidator(BaseValidator[ContentTypes]):
    error_code = "IN114"
    description = "Validate that there're no duplicated params for the integration."
    error_message = "The following params are duplicated: {0}.\nPlease make sure your file doesn't contain duplications."
    related_field = "configuration"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(duplicated_param_names)),
                content_object=content_item,
            )
            for content_item in content_items
            if (duplicated_param_names := self.is_containing_dups(content_item.params))
        ]

    def is_containing_dups(self, params) -> Set[str]:
        appeared_set = set()
        return set(
            param.get("name")
            for param in params
            if (
                param.get("name") in appeared_set or appeared_set.add(param.get("name"))
            )
        )
