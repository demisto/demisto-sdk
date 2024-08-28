from __future__ import annotations

from typing import Iterable, List
import os
from pathlib import Path

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack




class InvalidImageDimensionsValidator(BaseValidator[ContentTypes]):
    error_code = "IM112"
    description = "Ensures that the image file is not larger than 2 MB"
    rationale = "Keep packs lightweight"
    error_message = "Image: {} size is over 2 MB. Large files may be stored at the `demisto/content-assets` repository."
    related_field = "image"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.IMAGE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not self.is_image_size_valid(content_item.path)
        ]

    def is_image_size_valid(self, content_item: Path) -> bool:
        doc_files_path: str = f"{content_item}/doc_files"
        for image_path in Path(doc_files_path).iterdir():
            if image_path.is_file():
                if image_path.stat().st_size > 2 * 1024 * 1024:
                    self.error_message.format(image_path)
                    return False
        return True

