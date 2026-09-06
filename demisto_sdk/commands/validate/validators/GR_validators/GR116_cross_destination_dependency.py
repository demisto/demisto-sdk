from __future__ import annotations

from abc import ABC
from typing import Iterable, List, cast

from demisto_sdk.commands.content_graph.common import PackDestination
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class CrossDestinationDependencyValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Validate that Marketplace-only packs do not depend on "
        "Managed-Content-only packs."
    )
    rationale = (
        "A Marketplace pack that depends on a Managed-Content-only pack "
        "creates an unresolvable dependency for Marketplace consumers, "
        "since the managed pack is not available in the Marketplace bucket."
    )
    error_message = (
        "Pack '{content_id}' (destination: MARKETPLACE) depends on pack "
        "'{dep_id}' (destination: MANAGED_CONTENT). This cross-destination "
        "dependency is not allowed."
    )
    related_field = ""
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for pack in content_items:
            if pack.destination != PackDestination.MARKETPLACE:
                continue
            for dep in pack.depends_on:
                # `RelationshipData.content_item_to` is statically typed as the
                # generic `BaseNode`, but a DEPENDS_ON target of a pack is always
                # a `Pack` at runtime. The `hasattr` guard below is kept as-is so
                # runtime behavior is unchanged.
                dep_pack = cast(Pack, dep.content_item_to)
                if (
                    hasattr(dep_pack, "destination")
                    and dep_pack.destination == PackDestination.MANAGED_CONTENT
                ):
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                content_id=pack.object_id,
                                dep_id=dep_pack.object_id,
                            ),
                            content_object=pack,
                        )
                    )
        return results
