from __future__ import annotations

from typing import ClassVar, Iterable, List, Union

from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageExistValidator(BaseValidator[ContentTypes]):
    error_code = "DO108"
    description = "Validate that the given content item has a docker_image."
    error_message = "The {0} {1} is missing a docker image, please make sure to add one.\n The recommended default docker is {2}."
    related_field = "Docker image"
    is_auto_fixable = False
    latest_docker_dict: ClassVar[dict] = {}

    def get_latest_docker(self, content_item: ContentTypes):
        docker_suffix = (
            content_item.subtype if content_item.type == "python" else "powershell"
        )
        docker = f"demisto/{docker_suffix}"
        if docker not in DockerImageExistValidator.latest_docker_dict:
            DockerImageExistValidator.latest_docker_dict[
                docker
            ] = f"{docker}:{DockerImageValidator.get_docker_image_latest_tag_request(docker)}"
        return DockerImageExistValidator.latest_docker_dict[docker]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.name,
                    self.get_latest_docker(content_item),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.type == "javascript" and not content_item.docker_image
        ]
