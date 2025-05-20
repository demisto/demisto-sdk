from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsReleaseNotesFilledOutValidator(BaseValidator[ContentTypes]):
    error_code = "RN103"
    description = "Validate that the pack contains a full release note file."
    rationale = "Meaningful, complete documentations make it easier for users to use the content."
    error_message = (
        "Please complete the release notes and ensure all placeholders are filled in."
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )
    related_field = "release_note"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    @staticmethod
    def strip_exclusion_tag(release_notes_comments):
        """
        Strips the exclusion tag (<!-- -->) from the release notes since release notes should never
        be empty as this is poor user experience.
        Return:
            str. Cleaned notes with tags and contained notes removed.
        """
        return re.sub(r"<!--.*?-->", "", release_notes_comments, flags=re.DOTALL)

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
                path=content_item.release_note.file_path,
            )
            for content_item in content_items
            if content_item.release_note.exist
            and (
                not (
                    rn_stripped_content := self.strip_exclusion_tag(
                        content_item.release_note.file_content
                    )
                )
                or any(
                    note in rn_stripped_content
                    for note in [
                        "%%UPDATE_RN%%",
                        "%%XSIAM_VERSION%%",
                        "%%UPDATE_CONTENT_ITEM_CHANGE_DESCRIPTION%%",
                        "%%UPDATE_CONTENT_ITEM_DESCRIPTION%%",
                        "%%UPDATE_CONTENT_ITEM_NAME%%",
                        "%%UPDATE_CONTENT_ITEM_TYPE%%",
                    ]
                )
            )
        ]
