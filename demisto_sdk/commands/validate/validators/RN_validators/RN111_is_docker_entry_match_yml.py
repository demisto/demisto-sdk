from __future__ import annotations

from functools import cache
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import was_rn_added
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

NO_DOCKER_ENTRY_FOUND = "No docker entry found"

ContentTypes = Union[Integration, Script]


@cache
def release_notes_shouldbe_entry(content_item: IntegrationScript):
    """
    Get what image should be in the release notes
    Args:
        content_item: the content item to return the image for

    Returns: the image that should be in the rn, an empty string if none should be present

    """
    old_obj: IntegrationScript = content_item.old_base_content_object  # type: ignore
    if (
        old_obj and old_obj.docker_image == content_item.docker_image
    ):  # Wasn't set in this PR
        return ""
    return content_item.docker_image


def get_docker_image_entry(rn: str, content_item_name: str) -> str:
    """
    Get the docker image entry for a given content item
    Args:
        rn: the full release notes
        content_item_name: the content item to find the docker entry for

    Returns: the docker image in the rn or "NO_DOCKER_ENTRY_FOUND" constant if none found
    """
    rn_items = rn.split("##### ")
    docker = NO_DOCKER_ENTRY_FOUND
    for item in rn_items:
        if item.startswith(content_item_name):
            for entry in item.split("- "):
                if entry.startswith("Updated the Docker image to: "):
                    docker_entry = entry.replace("Updated the Docker image to: ", "")
                    docker = docker_entry[
                        docker_entry.find("*") + 1 : docker_entry.rfind("*")
                    ]
                    break
    return docker


def release_notes_mismatch_error(content_item: IntegrationScript):
    """
    Raises an error if:
    1: the image in the rn doesnt match what was bumped
    2: if an image was bumped but no release notes exist
    3: or if release notes exist but the image wasnt bumped
    """
    should_be_entry = release_notes_shouldbe_entry(content_item)
    image_entry = get_docker_image_entry(
        content_item.pack.release_note.file_content,
        content_item.display_name or content_item.name,
    )
    if should_be_entry and (
        should_be_entry not in image_entry or image_entry == NO_DOCKER_ENTRY_FOUND
    ):
        return f"Docker version in release notes should be {should_be_entry}, found: {image_entry}"
    if not should_be_entry and image_entry and not image_entry == NO_DOCKER_ENTRY_FOUND:
        return f"There should be no release notes docker update entry, found: {image_entry}"


class IsDockerEntryMatchYmlValidator(BaseValidator[ContentTypes]):
    error_code = "RN111"
    description = "Validate that the docker image version mentioned in the RN is indeed the one in the mentioned in the yml file."
    rationale = "We want to make sure we don't document wrong information."
    error_message = "The release notes regarding the docker image are not correct. {0}"
    related_field = "docker_image"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    is_auto_fixable = True

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
            if content_item.pack.release_note.exist
            and content_item.pack.release_note.git_status == GitStatuses.ADDED
            and (error := release_notes_mismatch_error(content_item))
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        """
        Update the release notes to contain the proper image entry, adds one if none exists.
        Deletes it if it shouldnt be there

        Args:
            content_item: the content item to fix the RN for
        Returns: a fix result

        """
        if not was_rn_added(content_item.pack):
            logger.debug(f"not fixing for {content_item.name} since rn was not added")
            raise ValueError("Release notes were not added, cannot fix.")
        should_be_rn_entry = release_notes_shouldbe_entry(content_item)
        should_be_full_rn = (
            f"- Updated the Docker image to: *{should_be_rn_entry}*."
            if should_be_rn_entry
            else ""
        )
        rn_items = content_item.pack.release_note.file_content.split("##### ")
        for item in rn_items:
            if not item.startswith(content_item.name):
                continue
            for entry in item.split("\n"):
                if entry.startswith("- Updated the Docker image to: "):
                    new_item = item.replace(
                        f"\n{entry}",
                        f"\n{should_be_full_rn}" if should_be_full_rn else "",
                    )
                    content_item.pack.release_note.file_content = (
                        content_item.pack.release_note.file_content.replace(
                            f"{item}", new_item
                        )
                    )
                    message = (
                        f"Changed docker update entry line in the release notes to match the yml: {should_be_rn_entry}."
                        if should_be_full_rn
                        else "Removed docker updated entry as it was not changed in the yml."
                    )
                    return FixResult(
                        validator=self,
                        message=message,
                        content_object=content_item,
                    )

            if should_be_full_rn:
                if item.endswith("\n\n"):
                    item = item[:-2]
                new_item = item + f"\n{should_be_full_rn}"
                content_item.pack.release_note.file_content = (
                    content_item.pack.release_note.file_content.replace(item, new_item)
                )
        return FixResult(
            validator=self,
            message=f"Added docker updated entry -{should_be_rn_entry}- in release notes.",
            content_object=content_item,
        )
