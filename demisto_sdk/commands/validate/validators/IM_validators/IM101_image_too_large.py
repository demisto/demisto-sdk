from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import (
    RelatedFileType,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

IMAGE_MAX_SIZE = 10 * 1024  # 10kB

ContentTypes = Integration


class ImageTooLargeValidator(BaseValidator[ContentTypes]):
    error_code = "IM101"
    description = "Checks that the image file size are matching the requirements."
    rationale = "Image needs to fit its place in the UI. For more information see: https://xsoar.pan.dev/docs/integrations/integration-logo"
    error_message = "You've created/modified a yml or package with a large sized image. Please make sure to change the image dimensions at: {0}."
    related_field = "image"
    related_file_type = [RelatedFileType.IMAGE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.path),
                content_object=content_item,
                path=content_item.image.file_path,
            )
            for content_item in content_items
            if content_item.image.exist and not self.is_image_valid(content_item)
        ]

    def is_image_valid(self, content_item: ContentTypes):
        file_type = content_item.image.file_path.suffix
        if file_type == ".png":
            return not content_item.image.get_file_size().st_size > IMAGE_MAX_SIZE

        elif file_type == ".svg":
            # No size validation done for SVG images
            return True

        elif file_type == ".yml":
            image_size = int(((len(content_item.data["image"]) - 22) / 4) * 3)
            return not image_size > IMAGE_MAX_SIZE

        # image can't be saved in a different file type
        return False
