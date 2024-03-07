from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DockerImageIsNotNativeImageValidator(BaseValidator[ContentTypes]):
    error_code = "DO102"
    description = "Validate that the given content item uses a docker image that is not the native image."
    rationale = "The 'native-image' Docker image is intended for internal development and should not be used for running integrations or scripts."
    error_message = "The docker image {0} is native-image, do not use a native-image"
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
            and content_item.docker_image.is_native_image
        ]
