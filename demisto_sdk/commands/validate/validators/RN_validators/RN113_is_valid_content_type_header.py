from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    CONTENT_TYPE_SECTION_REGEX,
    RN_HEADER_BY_FILE_TYPE,
    GitStatuses,
)
from demisto_sdk.commands.common.tools import (
    filter_out_falsy_values,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidContentTypeHeaderValidator(BaseValidator[ContentTypes]):
    error_code = "RN113"
    description = "Validate that the release note's first level headers which split the release notes by content types are valid content types."
    rationale = "Ensure we don't document false information."
    error_message = 'The following content type header(s) "{0}" are invalid.\nPlease use "demisto-sdk update-release-notes -i Packs/{1}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes'
    related_field = "Release notes"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        rn_valid_headers = RN_HEADER_BY_FILE_TYPE.values()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(invalid_headers), content_item.name
                ),
                content_object=content_item,
                path=content_item.release_note.file_path,
            )
            for content_item in content_items
            if (
                rn_sections := CONTENT_TYPE_SECTION_REGEX.findall(
                    content_item.release_note.file_content
                )
            )
            and (
                rn_first_level_headers := [
                    filter_out_falsy_values(ls=section)[0] for section in rn_sections
                ]
            )
            and (
                invalid_headers := [
                    rn_first_level_header
                    for rn_first_level_header in rn_first_level_headers
                    if rn_first_level_header not in rn_valid_headers
                ]
            )
        ]
