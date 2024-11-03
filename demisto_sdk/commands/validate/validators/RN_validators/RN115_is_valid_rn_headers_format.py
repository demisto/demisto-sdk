
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Pack


class IsValidRnHeadersFormatValidator(BaseValidator[ContentTypes]):
    error_code = "RN115"
    description = ""
    rationale = ""
    error_message = ""
    related_field = "Release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]


    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            invalid_headers = []
            headers = extract_rn_headers()
            filter_rn_headers(headers=headers)
            for content_type, content_items in headers.items():
                if not content_items:
                    results.append(ValidationResult(
                    validator=self,
                    message=self.error_message.format(content_type),
                    content_object=content_item,
                ))
        return results
