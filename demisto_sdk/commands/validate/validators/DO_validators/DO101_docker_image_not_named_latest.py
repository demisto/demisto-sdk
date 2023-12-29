from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
    FixResult
)


ContentTypes = Union[Integration, Script]


class LatestDockerImageValidator(BaseValidator[ContentTypes]):
    error_code = "DO101"
    description = "Validate that the given content-item does not use the 'latest' docker image, but always has a tag"
    error_message = "latest tag is not allowed, use versioned tag"
    related_field = "Docker image"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.type != "javascript"
            and content_item.docker_image.endswith("latest")
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.docker_image = content_item.object_id
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.object_id),
            content_object=content_item,
        )