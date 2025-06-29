from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsSupportedModulesRemoved(BaseValidator[ContentTypes]):
    error_code = "BC115"
    description = (
        "Ensure that no support module are removed from an existing content item."
    )
    rationale = "Removing a support module for content item can break functionality for customers."
    error_message = "The following support modules have been removed from the integration {}. Removing supported modules is not allowed, Please undo."
    related_field = "supportedModules"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.SCHEMA]

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
        old_params = set(old_item.supportedModules or [])
        new_params = set(new_item.supportedModules or [])
        return old_params.difference(new_params)
