from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Union

import requests
from dateparser import parse

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


class DockerImageTagIsNotOutdated(BaseValidator[ContentTypes]):
    error_code = "DO106"
    description = "Validate that the given content-item's docker image isnt outdated'"
    rationale = "Updated docker images ensure the code dont use outdated dependencies, including bugfixes and fixed vulnerabilities."
    error_message = "docker image {0}'s tag {1} is outdated. The latest tag is {2}"

    fix_message = "docker image {0} has been updated to {1}"
    related_field = "Docker image"
    is_auto_fixable = True

    @staticmethod
    def is_docker_image_older_than_three_months(docker_image: DockerImage) -> bool:
        """
        Return True if the docker image is more than 3 months old.

        Args:
            docker_image: the docker image object.
        """
        three_months_ago: datetime = parse("3 months ago")  # type: ignore[assignment]
        try:
            last_updated = docker_image.creation_date
            return not last_updated or three_months_ago > last_updated
        except DockerHubRequestException as error:
            if error.exception.response.status_code == requests.codes.not_found:
                logger.debug(
                    f"Could not get {docker_image} creation time because the image does not have the tag {docker_image.tag}"
                )
            else:
                logger.error(
                    f"Could not get {docker_image} creation time, error:{error}"
                )
            # return true if docker-image exist, but has a wrong tag
            return True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            if not content_item.is_javascript:
                docker_image = content_item.docker_image
                if not docker_image.is_valid:
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=f"Docker image {content_item.docker_image} format is invalid, cannot determine if it uses the latest tag",
                            content_object=content_item,
                        )
                    )
                    continue
                try:

                    docker_image_latest_tag = str(docker_image.latest_tag)
                except DockerHubRequestException as error:
                    logger.error(f"DO106 - Error when fetching latest tag:\n{error}")
                    if error.exception.response.status_code == requests.codes.not_found:
                        message = f"The docker-image {content_item.docker_image} does not exist, hence could not validate its latest tag"
                    else:
                        message = str(error)
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=message,
                            content_object=content_item,
                        )
                    )
                    continue
                if (
                    docker_image.tag != docker_image_latest_tag
                    and self.is_docker_image_older_than_three_months(docker_image)
                ):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                content_item.docker_image,
                                docker_image.tag,
                                docker_image_latest_tag,
                            ),
                            content_object=content_item,
                        )
                    )
        return invalid_content_items

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        docker_image = content_item.docker_image
        try:
            docker_image_latest_tag = docker_image.latest_docker_image
            message = self.fix_message.format(docker_image, docker_image_latest_tag)
            content_item.docker_image = docker_image_latest_tag
        except DockerHubRequestException as error:
            logger.error(
                f"Could not get the latest tag of {docker_image.name} when trying "
                f"to update latest docker-image tag of content-item {content_item.name}\nerror: {error}"
            )
            message = f"Could not update docker-image {docker_image}"

        return FixResult(
            validator=self,
            message=message,
            content_object=content_item,
        )
