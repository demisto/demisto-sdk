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

# TODO - need to implement
class DockerImageNotDemistoImageValidator(BaseValidator[ContentTypes]):
    error_code = "DO101"
    description = "Validate that the given content-item does not use the 'latest' docker image, but always has a tag"
    error_message = "docker image {0} has the 'latest' tag is which is not allowed, use versioned tag"
    fix_message = "docker image {0} has been updated to {1}"
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
            and content_item.docker_image
            and content_item.docker_image.endswith("latest")
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        docker_image = content_item.docker_image_object

        latest_docker_image = str(
            self.dockerhub_client.get_latest_docker_image_tag(docker_image.repository)
        )
        if content_item.docker_image:
            content_item.docker_image = content_item.docker_image.replace(
                "latest", latest_docker_image
            )
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                content_item.docker_image, latest_docker_image
            ),
            content_object=content_item,
        )
