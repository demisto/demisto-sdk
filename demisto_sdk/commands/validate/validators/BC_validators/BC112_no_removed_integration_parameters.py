from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class NoRemovedIntegrationParametersValidator(BaseValidator[ContentTypes]):
    error_code = "BC112"
    description = "Ensure that no parameters are removed from an existing integration."
    rationale = "Removed parameters can cause errors if the parameter is needed by the server of integration code."
    error_message = "Parameters have been removed from the integration, the removed parameters are: {}."
    related_field = "configuration"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(map(repr, sorted(difference)))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                difference := self.removed_parameters(
                    cast(ContentTypes, content_item.old_base_content_object),
                    content_item,
                )
            )
        ]

    def removed_parameters(self, old_item: ContentTypes, new_item: ContentTypes) -> set:
        old_params = {param.name for param in old_item.params}
        new_params = {param.name for param in new_item.params}
        return old_params.difference(new_params)
