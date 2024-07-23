from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    DEFAULT_DBOT_IMAGE_BASE64,
    DEFAULT_IMAGE,
    DEFAULT_IMAGE_BASE64,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class DefaultImageValidator(BaseValidator[ContentTypes]):
    error_code = "IM106"
    description = "Checks if the integration has an image other than the default ones."
    rationale = "If an image is provided, it must not be the default ones."
    error_message = "The integration is using the default image at {0}, please change to the integration image."
    related_field = "image"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.IMAGE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    DEFAULT_IMAGE,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.image.load_image()
                in [
                    DEFAULT_IMAGE_BASE64,
                    DEFAULT_DBOT_IMAGE_BASE64,
                ]
            )
        ]
