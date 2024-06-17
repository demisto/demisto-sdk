
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Integration


class IsValidDescriptionNameValidator(BaseValidator[ContentTypes]):
    error_code = "DS106"
    description = "Check if the description file exist and the name is valid"
    rationale = "Because we want a generic name for the files"
    error_message = ("The description's file is missing or the file name is invalid - "
                     "make sure the name looks like the following: <integration_name>_description.md "
                     "and that the integration_name is the same as the folder containing it.")

    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.ADDED]
    related_file_type = [RelatedFileType.DESCRIPTION_File]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not content_item.description_file.exist
            )
        ]
