
from __future__ import annotations

from typing import Iterable, List
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixResult,
        ValidationResult,
)
from demisto_sdk.commands.validate.validators.tools import extract_non_approved_tags, filter_by_marketplace

ContentTypes = Pack


class IsValidTagsValidator(BaseValidator[ContentTypes]):
    error_code = "PA120"
    description = "Validate that metadata's tag section include only approved tags."
    error_message = "The following tags {0} are invalid..."
    fix_message = ""
    related_field = "tags"
    is_auto_fixable = True

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        non_approved_tags = set()
        marketplaces = [x.value for x in list(MarketplaceVersions)]
        pack_tags, _ = filter_by_marketplace(marketplaces, content_item.pack_metadata_dict)
        non_approved_tags = extract_non_approved_tags(pack_tags, marketplaces)
        if non_approved_tags:
            if self._add_error(
                Errors.pack_metadata_non_approved_tags(non_approved_tags),
                self.pack_meta_file,
            ):
                return False
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.tags
            and USE_CASE_TAG in content_item.tags
            and not any(
                [
                    content_item.content_items.playbook,
                    content_item.content_items.incident_type,
                    content_item.content_items.layout,
                ]
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        pass
            
