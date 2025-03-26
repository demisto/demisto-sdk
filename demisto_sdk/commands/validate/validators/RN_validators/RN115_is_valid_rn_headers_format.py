from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import extract_rn_headers
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidRnHeadersFormatValidator(BaseValidator[ContentTypes]):
    error_code = "RN115"
    description = "Validate that the headers format are valid in a matter of spaces and other characters."
    rationale = "Ensure the Release notes has a generic structure to remain consistent."
    error_message = 'Did not find content items headers under the following content types: {0}. This might be due to invalid format.\nPlease use "demisto-sdk update-release-notes -i Packs/{1}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes'
    related_field = "Release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            headers = extract_rn_headers(
                content_item.release_note.file_content, remove_prefixes=True
            )
            if invalid_headers := [
                content_type
                for content_type, content_items in headers.items()
                if not content_items
            ]:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(invalid_headers), content_item.path.parts[-1]
                        ),
                        content_object=content_item,
                        path=content_item.release_note.file_path,
                    )
                )
        return results
