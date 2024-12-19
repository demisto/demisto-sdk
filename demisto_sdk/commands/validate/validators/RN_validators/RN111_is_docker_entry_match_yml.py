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
    error_message = "The docker entry in the release notes doesn't match what is in the yml.\n The docker image in rn: {0}, docker image in yml {1} - please make sure the dockers match."
    related_field = "docker_image"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    docker_entry, content_item.docker_image
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (old_obj := content_item.old_base_content_object)
            and content_item.docker_image != old_obj.docker_image  # type:ignore[attr-defined]
            and (
                docker_entry := self.get_docker_image_entry(
                    content_item.pack.release_note.file_content,
                    content_item.display_name,
                )
            )
            and content_item.docker_image not in docker_entry
        ]

    def get_docker_image_entry(self, rn: str, content_item_name: str) -> str:
        rn_items = rn.split("##### ")
        docker = "No docker entry found"
        for item in rn_items:
            if item.startswith(content_item_name):
                for entry in item.split("- "):
                    if entry.startswith("Updated the Docker image to: "):
                        docker_entry = entry.replace(
                            "Updated the Docker image to: ", ""
                        )
                        docker = docker_entry[
                            docker_entry.find("*") + 1 : docker_entry.rfind("*")
                        ]
                        break
        return docker
