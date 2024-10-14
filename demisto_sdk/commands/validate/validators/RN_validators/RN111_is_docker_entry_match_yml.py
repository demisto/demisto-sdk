from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsDockerEntryMatchYmlValidator(BaseValidator[ContentTypes]):
    error_code = "RN111"
    description = "Validate that the docker image version mentioned in the RN is indeed the one in the mentioned in the yml file."
    rationale = "We want to make sure we don't document wrong information."
    error_message = "The docker image that appears in the RN ({0}) is different from the one that appears in the yml, please make sure the files match."
    related_field = "docker_image"
    expected_git_statuses = [GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (old_obj := content_item.old_base_content_object)
            and content_item.docker_image != old_obj.docker_image
            and content_item.docker_image
            != self.get_docker_image_entry(content_item.pack, content_item.name)
        ]

    def get_docker_image_entry(pack, content_item_name) -> str:
        return ""
