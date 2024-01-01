from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack
APPROVED_PREFIXES = {x.value for x in list(MarketplaceVersions)}


class ValidTagsPrefixesValidator(BaseValidator[ContentTypes]):
    error_code = "PA100"
    description = "Validate that all the tags in tags field have a valid prefix."
    error_message = f"The pack metadata contains tag(s) with an invalid prefix: {0}.\nThe approved prefixes are: {', '.join(APPROVED_PREFIXES)}."
    related_field = "tags"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            temp_tags: List[str] = []
            for tag in content_item.tags or []:
                if ":" in tag:
                    tag_data = tag.split(":")
                    marketplaces = tag_data[0].split(",")
                    for marketplace in marketplaces:
                        if marketplace not in APPROVED_PREFIXES:
                            temp_tags.append(tag)
            if temp_tags:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format_map(", ".join(temp_tags)),  # type: ignore
                        content_object=content_item,
                    )
                )
        return validation_results
