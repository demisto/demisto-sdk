from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsTagsUnionSupersetOfPacksValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO106"
    description = (
        "Validates that a connector's metadata.tags contains the "
        "deduplicated union of the linked parent packs' tags."
    )
    rationale = (
        "A connector groups integrations from one or more parent packs. Its "
        "tags must cover every tag declared by those packs so no parent-pack "
        "tag is lost when the integrations are grouped into the connector."
    )
    error_message = (
        "Connector '{connector_id}' metadata.tags is missing tags from its "
        "linked parent packs: {missing}. Parent-pack tags union: {union}."
    )
    related_field = "metadata.tags"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            packs_tags: Set[str] = set()
            for handler in connector.xsoar_handlers:
                integration = handler.related_integration
                if integration is None:
                    continue
                pack = integration.in_pack
                if pack is None:
                    continue
                packs_tags.update(pack.tags or [])

            if not packs_tags:
                # No linked parent-pack tags to compare against.
                continue

            connector_tags = set(connector.connector_metadata.tags)
            missing = packs_tags - connector_tags

            if missing:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            missing=sorted(missing),
                            union=sorted(packs_tags),
                        ),
                        content_object=connector,
                    )
                )

        return results
