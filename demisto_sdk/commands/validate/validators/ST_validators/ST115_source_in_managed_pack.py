from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class SourceInManagedPackValidator(BaseValidator[Pack]):
    error_code = "ST115"
    description = "Validate that packs with 'managed: true' have a non-empty 'source' field in pack_metadata.json."
    rationale = "Managed packs must specify their source to maintain proper attribution and tracking."
    error_message = "Pack has 'managed: true' but is missing a non-empty 'source' field in pack_metadata.json. Please add a valid source."
    related_field = "source, managed"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[Pack]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.managed and not content_item.source
        ]
