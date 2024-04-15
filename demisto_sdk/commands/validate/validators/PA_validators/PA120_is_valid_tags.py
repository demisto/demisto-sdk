from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.tools import (
    extract_non_approved_tags,
    filter_by_marketplace,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidTagsValidator(BaseValidator[ContentTypes]):
    error_code = "PA120"
    description = "Validate that metadata's tag section include only approved tags."
    rationale = (
        "Using approved tags makes it easier for users to find the packs that suit their needs. "
        "For more info, see https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The pack metadata contains non approved tags: {0}. The list of approved tags for each marketplace can be found on https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    fix_message = "Removed the following tags: {0}."
    related_field = "tags"
    is_auto_fixable = True
    non_approved_tags_dict: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        marketplaces: List[str] = [x.value for x in list(MarketplaceVersions)]
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(non_approved_tags)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                non_approved_tags := self.get_non_approved_tags(
                    marketplaces, content_item
                )
            )
        ]

    def get_non_approved_tags(
        self, marketplaces: List[str], content_item: ContentTypes
    ) -> set:
        """Extract the set of non approved tag from the metadata's useCases field.

        Args:
            marketplaces (List[str]): The list of market places.
            content_item (ContentTypes): the pack_metadata object.

        Returns:
            set: the set of non approved tags.
        """
        non_approved_tags = set()
        if pack_tags := filter_by_marketplace(
            marketplaces, content_item.pack_metadata_dict, False  # type: ignore[arg-type]
        ):
            if non_approved_tags := extract_non_approved_tags(pack_tags, marketplaces):
                self.non_approved_tags_dict[content_item.name] = non_approved_tags
        return non_approved_tags

    def fix(self, content_item: ContentTypes) -> FixResult:
        tags = content_item.tags
        for non_approved_tag in self.non_approved_tags_dict[content_item.name]:
            tags.remove(non_approved_tag)
        content_item.tags = tags
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.non_approved_tags_dict[content_item.name])
            ),
            content_object=content_item,
        )
