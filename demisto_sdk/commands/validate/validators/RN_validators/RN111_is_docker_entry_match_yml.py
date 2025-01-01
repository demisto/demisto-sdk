from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult, FixResult,
)

NO_DOCKER_ENTRY_FOUND = "No docker entry found"

ContentTypes = Union[Integration, Script]


def release_notes_shouldbe_entry(content_item: IntegrationScript):
    old_obj = content_item.old_base_content_object
    if old_obj and old_obj.docker_image == content_item.docker_image:  # Wasn't set in this PR
        return ""
    return content_item.docker_image


def get_docker_image_entry(rn: str, content_item_name: str) -> str:
    rn_items = rn.split("##### ")
    docker = NO_DOCKER_ENTRY_FOUND
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


def release_notes_mismatch_error(content_item:IntegrationScript):
    should_be_entry = release_notes_shouldbe_entry(content_item)
    image_entry = get_docker_image_entry(content_item.pack.release_note.file_content, content_item.name)
    if should_be_entry and (not (should_be_entry in image_entry) or image_entry == NO_DOCKER_ENTRY_FOUND):
        return f"Docker version in release notes should be {should_be_entry}, found {image_entry}"
    if not should_be_entry and image_entry:
        return f"There should be no release notes docker update entry. Found {image_entry}"


class IsDockerEntryMatchYmlValidator(BaseValidator[ContentTypes]):
    error_code = "RN111"
    description = "Validate that the docker image version mentioned in the RN is indeed the one in the mentioned in the yml file."
    rationale = "We want to make sure we don't document wrong information."
    error_message = "The release notes regarding the docker image are not correct. {0}"
    related_field = "docker_image"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(error),
                content_object=content_item,
            )
            for content_item in content_items
            if (error := release_notes_mismatch_error(content_item))
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:

        should_be_rn_entry = release_notes_shouldbe_entry(content_item)
        should_be_full_rn = f'\n - here is my full thing {should_be_rn_entry}' if should_be_rn_entry else ''
        rn_items = content_item.pack.release_note.split("##### ")
        for item in rn_items:
            if not item.startswith(content_item.name):
                continue
            update_line_exists = False
            for entry in item.split("- "):
                if entry.startswith("Updated the Docker image to: "):
                    update_line_exists = True
                    new_item = item.replace(entry, should_be_full_rn)
                    content_item.pack.release_note = content_item.pack.release_note.replace(item, new_item)
                    break
            if not update_line_exists and should_be_full_rn:
                new_item = item + f'\n{should_be_full_rn}'
                content_item.pack.release_note = content_item.pack.release_note.replace(item, new_item)
                return FixResult(
                    validator=self,
                    message=f'Added "Updated the Docker.... {should_be_rn_entry} to the release notes.',
                    content_object=content_item,
                )