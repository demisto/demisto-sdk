from __future__ import annotations

from typing import Iterable, List, cast

from packaging.version import Version

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ContentItem


class IsValidToversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC107"
    description = "Checks that the `toversion` property was not changed on existing content, unless it is replaced by a new file with the same ID and a continuous fromversion."
    rationale = "Changing the `toversion` field for a content item can break backward compatibility."
    error_message = "Changing the maximal supported version field `toversion` is not allowed. unless you're adding new content_item with the same id {0} and their from/to version fulfills the following:\nThe old item `toversion` field should be less than the new item `fromversion` field\nThe old and the new item should be continuous, aka the old one `toversion` is one version less than the new one `fromversion`"
    related_field = "toversion"
    expected_git_statuses = [
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
        GitStatuses.ADDED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        modified_items, new_items = sort_content_items(content_items)
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.object_id),
                content_object=content_item,
            )
            for content_item in modified_items
            if self.invalid_toversion_modification(content_item, new_items)
        ]

    def invalid_toversion_modification(
        self, modified_item: ContentTypes, new_items: dict
    ):
        """
        Check if toversion field of a content item modification is valid.

        Args:
            modified_item (Iterable[ContentTypes]): The modified content item
            new_items (dict): the newly added content items

        Returns:
            weather it's valid or not.
        """
        old_file = cast(ContentTypes, modified_item.old_base_content_object)
        if modified_item.toversion != old_file.toversion:  # file toversion was updated
            if modified_item.object_id in new_items:
                new_item = new_items[modified_item.object_id]
                if not is_continuous_versions(
                    Version(modified_item.fromversion),
                    Version(modified_item.toversion),
                    Version(new_item.get("from")),
                ):
                    return True
            else:
                return True

        return False


def sort_content_items(content_items: Iterable[ContentTypes]):
    """
    Sort Content Items into two lists of Modified content items and newly added content items.

    Args:
        content_items (Iterable[ContentTypes]): The content items list

    Returns:
        modified_items: modified items.
        new_items: newly added items.
    """
    modified_items: list = []
    new_items: dict = {}
    for item in content_items:
        if item.git_status in [GitStatuses.MODIFIED, GitStatuses.RENAMED]:
            modified_items.append(item)
        elif item.git_status == GitStatuses.ADDED:
            new_items[item.object_id] = {"from": item.fromversion, "to": item.toversion}

    return modified_items, new_items


def is_continuous_versions(
    old_from: Version, old_to: Version, new_from: Version
) -> bool:
    """
    Check if two content items which one is replacing the other have valid continues from/to version.

    Args:
        old_from: the modified file `fromversion` field.
        old_to: the modified file `toversion` field.
        new_from: the newly added file `fromversion` field.

    Returns:
        whether the versions are valid or not.
    """
    res = [
        (
            old_to.major + 1 == new_from.major
            and new_from.minor == 0
            and new_from.micro == 0
        ),  # old_from 6.0.0, new_to 7.0.0
        (
            old_to.major == new_from.major
            and old_to.minor + 1 == new_from.minor
            and new_from.micro == 0
        ),  # old_from 6.0.0, new_to 6.1.0
        (
            old_to.major == new_from.major
            and old_from.minor == new_from.minor
            and old_to.micro + 1 == new_from.micro
        ),  # old_from 6.0.0, new_to 6.0.1
    ]
    is_continuous = any(res)
    return all(
        [
            old_from < new_from,  # old_from 6.0.0, new_from 8.9.0
            old_to < new_from,  # old_to 8.9.0, new_from 8.10.0
            is_continuous,
        ]
    )
