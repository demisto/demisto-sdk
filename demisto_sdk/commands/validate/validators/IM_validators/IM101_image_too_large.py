from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

IMAGE_MAX_SIZE = 10 * 1024  # 10kB

ContentTypes = Integration


class ImageTooLargeValidator(BaseValidator[ContentTypes]):
    error_code = "IM101"
    description = "Checks that the image file dimensions are matching the requirements."
    rationale = "Image needs to fit its place in the UI. For more information see: https://xsoar.pan.dev/docs/integrations/integration-logo"
    error_message = "You've created/modified a yml or package with a large sized image. Please make sure to change the image dimensions at: {0}."
    related_field = "image"
    related_file_type = [RelatedFileType.IMAGE]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name + "_image.png"),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.image.get_file_size().st_size > IMAGE_MAX_SIZE
        ]
