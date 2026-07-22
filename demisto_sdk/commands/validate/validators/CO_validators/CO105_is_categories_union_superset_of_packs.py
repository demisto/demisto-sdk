from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsCategoriesUnionSupersetOfPacksValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO105"
    description = (
        "Validates that a connector's metadata.categories contains the "
        "deduplicated union of the linked parent packs' categories."
    )
    rationale = (
        "A connector groups integrations from one or more parent packs. Its "
        "categories must cover every category declared by those packs so no "
        "parent-pack category is lost when the integrations are grouped into "
        "the connector."
    )
    error_message = (
        "Connector '{connector_id}' metadata.categories is missing "
        "categories from its linked parent packs: {missing}. "
        "Parent-pack categories union: {union}."
    )
    related_field = "metadata.categories"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            packs_categories: Set[str] = set()
            for handler in connector.xsoar_handlers:
                integration = handler.related_integration
                if integration is None:
                    continue
                pack = integration.in_pack
                if pack is None:
                    continue
                packs_categories.update(pack.categories or [])

            if not packs_categories:
                # No linked parent-pack categories to compare against.
                continue

            connector_categories = set(connector.connector_metadata.categories)
            missing = packs_categories - connector_categories

            if missing:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            missing=sorted(missing),
                            union=sorted(packs_categories),
                        ),
                        content_object=connector,
                    )
                )

        return results
