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
    rationale = "Ensure the readme file contains more details about the pack"
    description = "Checks if the README.md file is not same as the pack description."
    error_message = "README.md content is equal to pack description. Please remove the duplicate description from README.md file."
    related_field = "readme, description"
    related_file_type = [RelatedFileType.JSON, RelatedFileType.README]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.readme.file_content
                and content_item.description
                and content_item.description.lower().strip()
                == content_item.readme.file_content.lower().strip()
            )
        ]