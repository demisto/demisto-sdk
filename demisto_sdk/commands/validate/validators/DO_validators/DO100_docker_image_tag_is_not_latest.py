from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.docker.dockerhub_client import (
    DockerHubRequestException,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class LatestDockerImageTagValidator(BaseValidator[ContentTypes]):
    error_code = "DO100"
    description = "Validate that the given content-item does not use the tag 'latest' in its docker image"
    rationale = (
        "Locking content to use a specific tag of a docker image ensures stability. The tag is usually updated in newer versions of the content item."
        "For more details on Docker, visit https://xsoar.pan.dev/docs/integrations/docker."
    )
    error_message = (
        "docker image {0} has the 'latest' tag which is not allowed, use versioned tag"
    )
    fix_message = "docker image {0} has been updated to {1}"
    related_field = "Docker image"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.docker_image),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.is_javascript
            and content_item.docker_image.is_tag_latest
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        docker_image = content_item.docker_image
        try:
            latest_numeric_tag = docker_image.latest_tag
            message = self.fix_message.format(
                docker_image, f"{docker_image.name}:{latest_numeric_tag}"
            )
            content_item.docker_image = DockerImage(
                f"{docker_image.name}:{latest_numeric_tag}"
            )
        except DockerHubRequestException as error:
            logger.error(
                f"Could not get the latest tag of {docker_image.name} when trying "
                f"to update docker of content-item {content_item.name}\nerror: {error}"
            )
            message = f"Could not update docker-image {content_item.docker_image}"

        return FixResult(
            validator=self,
            message=message,
            content_object=content_item,
        )
