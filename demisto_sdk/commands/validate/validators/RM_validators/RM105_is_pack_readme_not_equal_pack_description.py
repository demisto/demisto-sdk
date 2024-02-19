from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsPackReadmeNotEqualPackDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "RM105"
    description = ""
    error_message = "README.md content is equal to pack description. Please remove the duplicate description from README.md file."
    related_field = ""
    is_auto_fixable = False
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
                content_item.readme
                and content_item.description
                and content_item.description.lower().strip()
                == content_item.readme.lower().strip()
            )
        ]
