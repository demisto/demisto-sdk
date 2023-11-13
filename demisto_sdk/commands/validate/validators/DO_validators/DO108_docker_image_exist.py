from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union["Integration", "Script"]


class DockerImageExistValidator(BaseValidator[ContentTypes]):
    error_code = "DO108"
    description = "Validate that the given content item has a docker_image."
    error_message = (
        "The {0} {1} is missing a docker image, please make sure to add one."
    )
    related_field = "Docker image"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type, content_item.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.docker_image
        ]
