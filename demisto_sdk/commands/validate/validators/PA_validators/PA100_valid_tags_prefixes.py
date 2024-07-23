from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack

APPROVED_PREFIXES = {x.value for x in list(MarketplaceVersions)}


class ValidTagsPrefixesValidator(BaseValidator[ContentTypes]):
    error_code = "PA100"
    description = "Validate that all the tags in tags field have a valid prefix."
    rationale = (
        "This standardization allows for efficient filtering and grouping in the marketplace. "
        "For more info about the valid tags see https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The pack metadata contains tag(s) with an invalid prefix: {0}.\nThe approved prefixes are: {1}."
    related_field = "tags"
    unapproved_tags_dict: ClassVar[dict] = {}
    is_auto_fixable = True
    fix_message = "removed the following invalid tags: {0}."

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(invalid_tags), ", ".join(APPROVED_PREFIXES)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_tags := self.get_invalid_tags(content_item))
        ]

    def get_invalid_tags(self, content_item: ContentTypes) -> List[str]:
        """Extract the list of invalid tags from the metadata file.

        Args:
            content_item (ContentTypes): the pack_metadata object.

        Returns:
            List[str]: the list of invalid tags.
        """
        invalid_tags = []
        for tag in content_item.tags or []:
            if ":" in tag:
                tag_data = tag.split(":")
                marketplaces = tag_data[0].split(",")
                for marketplace in marketplaces:
                    if marketplace not in APPROVED_PREFIXES:
                        invalid_tags.append(tag)
        self.unapproved_tags_dict[content_item.name] = invalid_tags
        return invalid_tags

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.tags = [
            tag
            for tag in content_item.tags
            if tag not in self.unapproved_tags_dict[content_item.name]
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.unapproved_tags_dict[content_item.name])
            ),
            content_object=content_item,
        )
