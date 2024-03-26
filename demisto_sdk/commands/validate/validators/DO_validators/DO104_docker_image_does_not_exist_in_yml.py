from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageExistValidator(BaseValidator[ContentTypes]):
    error_code = "DO104"
    description = "Validate that the given content item has a docker_image."
    rationale = "Python and Powershell content run in containers."
    error_message = "The {0} {1} is missing a docker image.\n The recommended default docker is {2}."
    related_field = "Docker image"
    is_auto_fixable = False

    @staticmethod
    def get_latest_image(content_item):
        docker_name = f"demisto/{content_item.subtype if content_item.type == 'python' else 'powershell'}"
        return DockerHubClient().get_latest_docker_image(docker_name)

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.name,
                    self.get_latest_image(content_item),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.is_javascript and not content_item.docker_image
        ]
