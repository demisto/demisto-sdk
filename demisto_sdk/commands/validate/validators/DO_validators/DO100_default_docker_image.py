from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DefaultDockerImageValidator(BaseValidator[ContentTypes]):
    error_code = "DO100"
    description = (
        "Validate that the given content item's docker_image is not "
        "the default docker demisto/python:1.3-alpine"
    )
    error_message = (
        "The current docker image in the yml file is the default one: "
        "demisto/python:1.3-alpine, Please create or use another docker image"
    )
    related_field = "Docker image"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.type == "javascript"
            and content_item.docker_image == "demisto/python:1.3-alpine"
        ]
