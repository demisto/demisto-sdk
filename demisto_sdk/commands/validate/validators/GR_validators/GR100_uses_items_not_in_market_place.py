from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.common import RelationshipType

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = BaseContent


class MarketplacesFieldValidator(BaseValidator[ContentTypes]):
    error_code = "GR100"
    description = (
        "Detect content items that attempt to use other content items which are not supported in all of the "
        "marketplaces of the content item."
    )
    rationale = "Content graph proper construction."
    error_message = ("Content item '{content_name}' can be used in the '{marketplaces}' marketplaces,"
                     " however it uses content items: '{used_content_items}'"
                     " which are not supported in all of the marketplaces of '{content_name}'.")

    related_field = "marketplaces"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validation_results = []

        for content_item in self.graph.find_uses_paths_with_invalid_marketplaces(
            [item.pack_id for item in content_items]
        ):

            used_content_items = [
                item.content_item_to.object_id
                for item in content_item.relationships_data.get(RelationshipType.USES)
            ]

            validation_results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(content_name=content_item.name,
                                                      marketplaces=', '.join(content_item.marketplaces),
                                                      used_content_items=', '.join(used_content_items)),
                    content_object=content_item,
                )
            )
        return validation_results
