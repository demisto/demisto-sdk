from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import check_text_content_contain_sub_text
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Pack, Integration, Script, Playbook]


class IsContainDemistoWordValidator(BaseValidator[ContentTypes]):
    error_code = "RM106"
    description = (
        "Validate that none of the readme lines contains the the word 'demisto'."
    )
    rationale = (
        "Ensure that the current name of the product is used rather than the old one."
    )
    error_message = "Invalid keyword 'demisto' was found in lines: {0}. For more information about the README See https://xsoar.pan.dev/docs/documentation/readme_file."
    related_field = "readme"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

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
                    text=content_item.readme.file_content,
                )
            )
        ]
