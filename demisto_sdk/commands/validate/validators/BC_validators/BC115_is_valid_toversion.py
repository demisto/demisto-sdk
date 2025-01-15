from __future__ import annotations

from typing import Iterable, List, cast, Union
from packaging.version import Version

from demisto_sdk.commands.common.constants import GitStatuses
# from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[ModelingRule, ParsingRule, CorrelationRule]


class IsValidToversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC115"
    description = (
        "Check that the toversion property is valid."
    )
    rationale = "Changing the `toversion` field for a content item should include adding a new item to replace it."
    # error_message = "Changing the maximal supported version field `toversion` is not valid. No new item to replace it."
    error_message = "{0}"
    related_field = "toversion"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED, GitStatuses.ADDED]  # todo: do we need renamed?
    valid_cases = ("The old {0} `fromversion` field should be less than the new {0} `fromversion` field\n"
                   "The old {0} `toversion` field should be less than the new {0} `fromversion` field\n"
                   "The old and the new {0} should be continuous, aka the old one `toversion` is one version"
                   " less than the new one `fromversion`")
    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        modified_items, new_items = sort_content_items(content_items)
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(err_message),
                content_object=content_item,
            )
            for content_item in modified_items
            if (err_message := self.toversion_invalid(content_item, new_items))
        ]

    def toversion_invalid(self, modified_item: ContentTypes, new_items: dict):

        old_file = cast(ContentTypes, modified_item.old_base_content_object)
        if modified_item.toversion != old_file.toversion:  # file toversion was updated
            if modified_item.content_type.value in ['ModelingRule', 'ParsingRule']:
                return self.is_valid_item(modified_item.pack_name, modified_item, new_items)
                # # Found a new content item that's replacing it
                # if modified_item.pack_name in new_items and modified_item.content_type.value == new_items.get('type'):
                #     new_item = new_items[modified_item.pack_name]
                #     is_valid_results = is_valid_versions(Version(modified_item.fromversion),
                #                                          Version(modified_item.toversion),
                #                                          Version(new_item.get('from')))
                #     if not all(is_valid_results):
                #         return (f"Invalid Change in the {modified_item.content_type.value} versions please validate the"
                #                 f" following points:\n{self.valid_cases.format(modified_item.content_type.value)}")
                # else:
                #     return ("Changing the maximal supported version field `toversion` is not allowed without adding"
                #             " a new content item to replace it.")
            elif modified_item.content_type.value in ['CorrelationRule']:
                return self.is_valid_item(modified_item.object_id, modified_item, new_items)

            return
        return

    def is_valid_item(self, item_key, modified_item: ContentTypes, new_items: dict):

        # Found a new content item that's replacing it
        if item_key in new_items and modified_item.content_type.value == new_items[item_key].get('type'):
            new_item = new_items[item_key]
            is_valid_results = is_valid_versions(Version(modified_item.fromversion),
                                                 Version(modified_item.toversion),
                                                 Version(new_item.get('from')))
            if not all(is_valid_results):
                return (f"Invalid Change in the {modified_item.content_type.value} versions please validate the"
                        f" following points:\n{self.valid_cases.format(modified_item.content_type.value)}")
        else:
            return ("Changing the maximal supported version field `toversion` is not allowed without adding"
                    " a new content item to replace it.")


def sort_content_items(content_items: Iterable[ContentTypes]):
    modified_items: list = []
    new_items: dict = {}
    for item in content_items:
        if item.git_status == GitStatuses.MODIFIED:
            modified_items.append(item)
        elif item.git_status == GitStatuses.ADDED:
            if item.content_type.value in ['ModelingRule', 'ParsingRule']:
                new_items[item.pack_name] = {'from': item.fromversion, 'to': item.toversion, 'type': item.content_type.value}
            if item.content_type.value in ['CorrelationRule']:
                new_items[item.object_id] = {'from': item.fromversion, 'to': item.toversion, 'type': item.content_type.value}

    return modified_items, new_items


def is_valid_versions(old_from: Version, old_to: Version, new_from: Version) -> list[bool]:
    res = [
        (old_to.major + 1 == new_from.major and new_from.minor == 0 and new_from.micro == 0),
        (old_to.major == new_from.major and old_to.minor + 1 == new_from.minor and new_from.micro == 0),
        (old_to.major == new_from.major and old_from.minor == new_from.minor and old_to.micro + 1 == new_from.micro)
    ]
    is_continuous = any(res)
    results = [
        old_from < new_from,
        old_to < new_from,
        is_continuous,
    ]
    return results