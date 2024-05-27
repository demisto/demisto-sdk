from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import check_text_content_contain_sub_text
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsDescriptionContainsDemistoWordValidator(BaseValidator[ContentTypes]):
    error_code = "DS107"
    description = (
        "Validate that none of the description lines contains the the word 'demisto'."
    )
    rationale = (
        "Ensure that the current name of the product is used rather than the old one."
    )
    error_message = "Invalid keyword 'demisto' was found in lines: {0}. For more information about the description file See: https://xsoar.pan.dev/docs/documentation/integration-description."
    related_field = "description"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.DESCRIPTION_File]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(lines_contain_demsito)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                lines_contain_demsito := check_text_content_contain_sub_text(
                    sub_text_list=["demisto"],
                    is_lower=True,
                    text=content_item.description_file.file_content,
                )
            )
        ]
