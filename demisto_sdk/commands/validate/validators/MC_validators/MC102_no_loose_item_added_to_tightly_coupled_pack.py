from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.upload.constants import CONTENT_TYPES_EXCLUDED_FROM_UPLOAD
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    GitStatuses,
    ValidationResult,
)

ContentTypes = ContentItem

# Test-only items never reach Managed Content, so they affect neither the classification nor the report.
IGNORED_CONTENT_TYPES = CONTENT_TYPES_EXCLUDED_FROM_UPLOAD

# A content item is identified by its type and id: ids are unique per type only.
ItemKey = Tuple[ContentType, str]


def _item_key(content_item: ContentItem) -> ItemKey:
    return (content_item.content_type, content_item.object_id)


def _resolve_full_pack(pack: Pack) -> Pack:
    """Return the pack with ``content_items`` populated, re-parsing it when ``in_pack`` resolved metadata only."""
    if pack.content_items:
        return pack
    full_pack = BaseContent.from_path(pack.path)
    return full_pack if isinstance(full_pack, Pack) else pack


class NoLooseItemAddedToTightlyCoupledPackValidator(BaseValidator[ContentTypes]):
    error_code = "MC102"
    description = (
        "Validate that a loosely coupled content item is not added to an existing "
        "pack whose content items are all tightly coupled."
    )
    rationale = (
        "A pack whose content items are all tightly coupled is carried in full into "
        "its Managed Content twin. Adding a loosely coupled item forces the pack to "
        "be split between Marketplace and Managed Content, changing the way it is "
        "delivered and installed."
    )
    error_message = (
        "Cannot add the loosely coupled {0} '{1}' to pack '{2}': all the pack's "
        "existing content items are tightly coupled, so the pack is carried in full "
        "into Managed Content and must stay that way. Add the item to a different "
        "pack."
    )
    related_field = "content_items"
    expected_git_statuses = [GitStatuses.ADDED]
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        packs: Dict[str, Pack] = {}
        added_items_by_pack: Dict[str, List[ContentTypes]] = defaultdict(list)

        for content_item in content_items:
            if content_item.content_type in IGNORED_CONTENT_TYPES:
                continue
            if not (pack := content_item.in_pack):
                continue
            packs.setdefault(pack.pack_id, _resolve_full_pack(pack))
            added_items_by_pack[pack.pack_id].append(content_item)

        results: List[ValidationResult] = []
        for pack_id, added_items in added_items_by_pack.items():
            pack = packs[pack_id]
            if not self._was_pack_fully_tightly_coupled(pack, added_items):
                continue
            results.extend(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_item.content_type.value,
                        content_item.object_id,
                        pack_id,
                    ),
                    content_object=content_item,
                )
                for content_item in added_items
                if not pack._is_item_tightly_coupled(content_item)
            )
        return results

    @staticmethod
    def _was_pack_fully_tightly_coupled(
        pack: Pack, added_items: List[ContentTypes]
    ) -> bool:
        """True when the pack splits and every pre-existing item was tightly coupled."""
        if not pack.is_managed_paired():
            return False

        added_keys: Set[ItemKey] = {_item_key(item) for item in added_items}
        pre_existing_items = [
            item
            for item in pack.content_items
            if item.content_type not in IGNORED_CONTENT_TYPES
            and _item_key(item) not in added_keys
        ]
        if not pre_existing_items:
            return False
        return all(pack._is_item_tightly_coupled(item) for item in pre_existing_items)
