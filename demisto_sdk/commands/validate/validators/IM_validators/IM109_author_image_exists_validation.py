from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack

class AuthorImageExistsValidator(BaseValidator[ContentTypes]):
    error_code = "IM109"
    description = "Checks if the pack has an author image path."
    error_message = "Partner, You've created/modified a yml or package without providing an author image as a .png file , please add an image in order to proceed."
    related_field = "image"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.AUTHOR_IMAGE]

    
    def is_valid(self, content_items: Iterable[ContentTypes])->List[ValidationResult]:
        return [
            ValidationResult(
            validator=self,
            message= self.error_message,
            content_object=content_item)
            
            for content_item in content_items
            if content_item.support == "partner" and (not Path(content_item.author_image_path).is_file() or not Path(content_item.author_image_path).exists())
        ]

