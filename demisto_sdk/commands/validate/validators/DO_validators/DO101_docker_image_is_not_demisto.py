from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageIsNotDemistoValidator(BaseValidator[ContentTypes]):
    error_code = "DO101"
    description = "Validate that the given content-item uses demisto docker image"
    error_message = "docker image {0} is not a valid docker-image, docker-image should start with demisto/"
    related_field = "Docker image"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.docker_image),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.is_javascript
            and not content_item.docker_image.is_demisto_repository
        ]
