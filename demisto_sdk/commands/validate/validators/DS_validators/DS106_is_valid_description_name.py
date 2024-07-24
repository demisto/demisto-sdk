from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDescriptionNameValidator(BaseValidator[ContentTypes]):
    error_code = "DS106"
    description = "Check if the description file exist and the name is valid."
    rationale = (
        "We want to make sure all integrations have all required documentation"
        " and that the file name is according to our standards."
    )
    error_message = (
        "The description's file is missing or the file name is invalid - "
        "make sure the name looks like the following: {0}."
    )

    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.ADDED]
    related_file_type = [RelatedFileType.DESCRIPTION_File]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.description_file.file_path.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.description_file.exist)
        ]
