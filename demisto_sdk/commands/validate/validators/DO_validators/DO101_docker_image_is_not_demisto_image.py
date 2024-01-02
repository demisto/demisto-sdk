from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]

# TODO - need to think about implementation

class DockerImageNotDemistoImageValidator(BaseValidator[ContentTypes]):
    error_code = "DO101"
    description = "Validate that the given content-item does uses the demisto docker image"
    error_message = "docker image {0} is not a demisto docker image"
    fix_message = "docker image {0} has been updated to {1}"
    related_field = "Docker image"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        demisto_docker_images = self.dockerhub_client.get_repository_images_names("demisto")
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.type != "javascript"
            and self.dockerhub_client.get_image_tags(content_item.docker_image_object.repository)
        ]

