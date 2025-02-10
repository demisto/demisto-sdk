from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class AuthorImageIsEmptyValidator(BaseValidator[ContentTypes]):
    error_code = "IM108"
    description = "Checks that the author image file is not empty"
    rationale = (
        "If an author image is provided, it must be a valid image. "
        "For more info, see: https://xsoar.pan.dev/docs/packs/packs-format#author_imagepng"
    )
    error_message = (
        "The author image should not be empty. Please provide a relevant image."
    )
    related_field = "image"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.AUTHOR_IMAGE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
                path=content_item.author_image_file.file_path,
            )
            for content_item in content_items
            if content_item.author_image_file.exist
            and (content_item.author_image_file.get_file_size().st_size == 0)
        ]
