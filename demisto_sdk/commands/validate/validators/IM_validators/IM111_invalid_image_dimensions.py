from __future__ import annotations

from typing import Iterable, List

import imagesize

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

IMAGE_WIDTH = 120
IMAGE_HEIGHT = 50
ContentTypes = Integration


def is_image_dimensions_valid(content_item: ContentTypes) -> bool:
    if content_item.image.exist:
        return (IMAGE_WIDTH, IMAGE_HEIGHT) == imagesize.get(
            content_item.image.file_path
        )
    return True


class InvalidImageDimensionsValidator(BaseValidator[ContentTypes]):
    error_code = "IM111"
    description = "Checks that the image file dimensions are matching the requirements."
    rationale = "Image needs to fit its place in the UI. For more information see: https://xsoar.pan.dev/docs/integrations/integration-logo"
    error_message = "The image dimensions do not match the requirements. A resolution of 120x50 pixels is required."
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
                path=content_item.image.file_path,
            )
            for content_item in content_items
            if not is_image_dimensions_valid(content_item)
        ]
