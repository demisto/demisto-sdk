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


class ReleaseNoteHeaderContentTypeValidator(
    ReleaseNoteHeaderValidator, BaseValidator[ContentTypes]
):

    error_message = (
        "The content header(s) type are invalid: {}"
        "For common troubleshooting steps, please review the documentation found here: "
        "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
    )

    def validate_release_notes_headers(self, content_item):
        """
        Validate that the release notes type headers are valid:
        - Validate that the release notes 1st headers are a valid content entity.

        Args:
            content_item: The content item to validate.

        Returns:
            Array: The 1st headers if headers are invalid, or an empty array if the headers are valid.
        """

        headers = self.extract_rn_headers(content_item.release_note.file_content)
        invalid_headers_type: List[str] = [
            header_type
            for header_type in headers.keys()
            if not self.validate_content_type_header(header_type)
        ]
        return invalid_headers_type
