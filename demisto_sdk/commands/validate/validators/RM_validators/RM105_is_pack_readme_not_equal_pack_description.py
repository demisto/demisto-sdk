from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsPackReadmeNotEqualPackDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "RM105"
    rationale = (
        "An informative README helps users know more about the product and its uses."
    )
    description = "Checks if the README.md file is not same as the pack description."
    error_message = (
        "README.md content is identical to the pack description. "
        "Add more information to the README. "
        "See https://xsoar.pan.dev/docs/documentation/readme_file for more information."
    )
    related_field = "readme, description"
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (
                content_item.readme.file_content
                and content_item.description
                and content_item.description.lower().strip()
                == content_item.readme.file_content.lower().strip()
            )
        ]
