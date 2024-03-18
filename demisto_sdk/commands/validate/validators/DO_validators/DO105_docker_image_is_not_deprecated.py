from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List, Union

from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageIsNotDeprecatedValidator(BaseValidator[ContentTypes]):
    error_code = "DO105"
    description = "Validate that the given content item uses a docker image that is not deprecated"
    rationale = "It is best practice to use images that are maintained by the platform."
    error_message = "The {0} docker image is deprecated, {1}"
    related_field = "Docker image"
    is_auto_fixable = False
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
                        content_item.docker_image.name
                    ),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.is_javascript
            and self.deprecated_dockers_to_reasons.get(content_item.docker_image.name)
        ]
