from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import VERSION_REGEX
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsCurrentVersionCorrectFormatValidator(BaseValidator[ContentTypes]):
    error_code = "PA130"
    description = "Validate that the pack_metadata version field is in valid format."
    rationale = "Content versions use semantic versioning to make it easy to tell how significant changes are between two versions."
    error_message = "Pack metadata version format is not valid. Please fill in a valid format (example: 0.0.0)"
    related_field = "currentVersion"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not re.match(VERSION_REGEX, content_item.current_version)  # type: ignore
        ]
