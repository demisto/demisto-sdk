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


def is_image_size_valid(content_item: Path) -> bool:
    doc_files_path: str = f"{content_item}/doc_files"
    for image_name in os.listdir(doc_files_path):
        image_path = Path(f"{doc_files_path}/{image_name}")
        if os.path.isfile(image_path):
            if os.path.getsize(image_path) > 2 * 1024 * 1024:
                return False
    return True


class InvalidImageDimensionsValidator(BaseValidator[ContentTypes]):
    error_code = "IM112"
    description = "Ensures that the image file is not larger than 2 MB."
    rationale = "In order to avoid large packages."
    error_message = "Image size is over 2 MB. Please reduce it or store it in demisto/content-assets repository."
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
            if not is_image_size_valid(content_item.path)
        ]
