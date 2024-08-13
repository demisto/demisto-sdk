from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsRNAddedToNewPackValidator(BaseValidator[ContentTypes]):
    error_code = "RN108"
    description = "Validate that a new pack doesn't have a RN,"
    rationale = (
        "New Packs doesn't require release notes since they don't have any updates."
    )
    error_message = "The Pack is a new pack and contains release notes, please remove all release notes."
    related_field = "Release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.release_note.all_rns)
        ]
