from __future__ import annotations

from typing import List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN114_validate_release_notes_header import (
    ReleaseNoteHeaderValidator,
)

ContentTypes = Pack


class ReleaseNoteHeaderContentItemValidator(
    ReleaseNoteHeaderValidator, BaseValidator[ContentTypes]
):
    error_message = (
        "The content header(s) Item are invalid:{}"
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )

    def validate_release_notes_headers(self, content_item):
        """
        Validate that the release notes headers are valid:
        - Validate that the 2nd headers exist in the pack and have the correct display name.

        Args:
            content_item: The content item to validate.

        Returns:
            Array: The 2nd headers if headers are invalid, or an empty array if the headers are valid.
        """

        invalid_headers_content_item: List[str] = []
        headers = self.extract_rn_headers(content_item.release_note.file_content)

        for header_type, header_content_items in headers.items():
            invalid_items = self.validate_content_item_header(
                header_type, header_content_items, content_item
            )
            if invalid_items:
                invalid_headers_content_item.extend(invalid_items)
        return invalid_headers_content_item
