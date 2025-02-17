from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class NoDescriptionFileValidator(BaseValidator[ContentTypes]):
    error_code = "DS104"
    description = "Verifies that a Description file is present for an integration and the name is valid."
    rationale = "It is recommended to have a Description file for each integration, which for example will have additional details on how to configure the instance."
    error_message = (
        "The description's file is missing or the file name is invalid - "
        "make sure the name looks like the following: {0}."
    )
    related_field = "description file"
    is_auto_fixable = False
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
            if (not (content_item.is_unified or content_item.description_file.exist))
        ]
