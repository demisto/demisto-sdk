from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RN_HEADER_BY_FILE_TYPE, GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import extract_rn_headers, filter_rn_headers
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidContentTypeHeaderValidator(BaseValidator[ContentTypes]):
    error_code = "RN113"
    description = ""
    rationale = ""
    error_message = 'The following content types header(s) "{0}" are either an invalid content type or does not exist in the "{pack_name}" pack.\nPlease use "demisto-sdk update-release-notes -i Packs/{1}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes'
    related_field = "Release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        rn_valid_headers = RN_HEADER_BY_FILE_TYPE.values()
        for content_item in content_items:
            headers = extract_rn_headers(content_item.release_note.file_content)
            filter_rn_headers(headers=headers)
            invalid_headers = [
                content_type
                for content_type in rn_valid_headers
                if content_type not in rn_valid_headers
            ]
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        ", ".join(invalid_headers), content_item.name
                    ),
                    content_object=content_item,
                )
            )
        return results
