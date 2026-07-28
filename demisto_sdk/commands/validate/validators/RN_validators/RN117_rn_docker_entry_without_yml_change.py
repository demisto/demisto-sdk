from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN111_is_docker_entry_match_yml import (
    NO_DOCKER_ENTRY_FOUND,
    get_docker_image_entry,
    release_notes_shouldbe_entry,
)

ContentTypes = Union[Integration, Script]


def rn_docker_entry_without_yml_change(content_item: IntegrationScript) -> str:
    """
    Return the docker image mentioned in the release notes when the yml docker
    image was NOT actually bumped in this PR.

    Args:
        content_item: the content item to check the release notes for.

    Returns: the docker image string found in the release notes, or an empty
        string when there is no violation (the yml was bumped, or the release
        notes contain no docker entry).
    """
    if release_notes_shouldbe_entry(content_item):
        # The yml docker image was bumped in this PR, so an RN entry is expected.
        return ""
    image_entry = get_docker_image_entry(
        content_item.pack.release_note.file_content,
        content_item.display_name or content_item.name,
    )
    if image_entry and image_entry != NO_DOCKER_ENTRY_FOUND:
        return image_entry
    return ""


class RNDockerEntryWithoutYmlChangeValidator(BaseValidator[ContentTypes]):
    error_code = "RN117"
    description = "Validate that a docker image update entry in the release notes corresponds to an actual docker image change in the yml file."
    rationale = "A release note that claims a docker image update when the yml docker image did not actually change documents an update that never happened, misleading users."
    error_message = "The release notes mention a docker image update ('{0}') but the docker image in the yml file was not changed. Remove the docker update entry from the release notes or update the docker image in the yml file."
    related_field = "docker_image"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(image_entry),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.pack.release_note.exist
            and content_item.pack.release_note.git_status == GitStatuses.ADDED
            and (image_entry := rn_docker_entry_without_yml_change(content_item))
        ]
