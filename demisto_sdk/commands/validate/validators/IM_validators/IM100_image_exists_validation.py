from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.common.tools import os
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class ImageExistsValidator(BaseValidator[ContentTypes]):
    error_code = "IM100"
    description = "Checks if the integration has an image path."
    error_message = "You've created/modified a yml or package without providing an image as a .png file , please add an image in order to proceed."
    related_field = "image"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.IMAGE]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
             ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.image_file and not Path(content_item.image_file).is_file() or not content_item.image_file]
