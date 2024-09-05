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


class MultipleRNsAddedValidator(BaseValidator[ContentTypes]):
    error_code = "RN105"
    description = "Validate there're no more than one Added rn for each pack."
    rationale = "Having more than one release note for a version may cause confusion and missing information."
    error_message = "The pack contains more than one new release note, please make sure the pack contains at most one release note."
    related_field = "release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
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
            if (
                content_item.old_base_content_object
                and len(
                    added_rns := set(content_item.release_note.all_rns)
                    - set(content_item.old_base_content_object.release_note.all_rns)  # type:ignore[attr-defined]
                )
                > 1
                and len([rn for rn in added_rns if rn.endswith(".md")]) > 1
            )
        ]
