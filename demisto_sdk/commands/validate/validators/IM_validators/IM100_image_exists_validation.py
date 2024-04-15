from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class ImageExistsValidator(BaseValidator[ContentTypes]):
    error_code = "IM100"
    description = "Checks if the integration has an image path."
    error_message = "You've created/modified a yml or package without providing an image as a .png file. Please make sure to add an image at"
    related_field = "image"
    rationale = "Images make it easier to find integrations"
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.IMAGE]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=f"{self.error_message} {content_item.name}_image.png.",
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.image.exist
        ]
