from __future__ import annotations

import re
from typing import ClassVar, Dict, Iterable, List, Union

from demisto_sdk.commands.common.docker.dockerhub_client import (
    DockerHubRequestException,
)
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageIsNotDeprecatedValidator(BaseValidator[ContentTypes]):
    error_code = "DO109"
    description = "Validate that the given content item uses a docker image that is not deprecated"
    error_message = "The {0} docker image is deprecated, {1}"
    related_field = "Docker image"
    fix_message = "deprecated docker image {0} has been updated to {1}"
    is_auto_fixable = True
    deprecated_dockers_to_reasons: ClassVar[
        Dict[str, str]
    ] = {}  # map between deprecated docker to the reason its deprecated

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:

        if not self.deprecated_dockers_to_reasons:
            deprecated_dockers = JsonFile.read_from_github_api(
                path="/docker/deprecated_images.json",
                git_content_config=GitContentConfig(repo_name="demisto/dockerfiles"),
                verify_ssl=False,
            )
            DockerImageIsNotDeprecatedValidator.deprecated_dockers_to_reasons = {
                record.get("image_name", ""): record.get("reason")
                for record in deprecated_dockers
            }

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.docker_image,
                    self.deprecated_dockers_to_reasons.get(
                        content_item.docker_image_object.name
                    ),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.is_javascript
            and self.deprecated_dockers_to_reasons.get(
                content_item.docker_image_object.name
            )
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        docker_image = content_item.docker_image_object
        if match := re.search(
            r"(demisto/[^ ]+)", self.deprecated_dockers_to_reasons[docker_image.name]
        ):
            recommended_docker_image_name = match.group(1)
            try:
                content_item.docker_image = f"{recommended_docker_image_name}:{self.dockerhub_client.get_latest_docker_image_tag(recommended_docker_image_name)}"
                message = self.fix_message.format(
                    docker_image,
                    content_item.docker_image,
                )
            except DockerHubRequestException as error:
                logger.error(
                    f"Could not get the latest tag of {recommended_docker_image_name} when trying "
                    f"to update deprecated docker of content-item {content_item.name}\nerror: {error}"
                )
                message = f"Could not update docker-image {docker_image}"
        else:
            message = f"Could not update docker-image {docker_image}"

        return FixResult(
            validator=self,
            message=message,
            content_object=content_item,
        )
