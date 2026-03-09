from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Set

from demisto_sdk.commands.common.constants import BASE_PACK
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack

# These are the currently allowed (existing) dependencies for the Base pack.
# No new dependencies should be added.
BASE_PACK_ALLOWED_DEPENDENCIES: Set[str] = {"Core", "AggregateScripts"}


class IsBasePackHasNoNewDependenciesValidator(BaseValidator[ContentTypes], ABC):
    error_code = "PA133"
    description = (
        "Validates that the Base pack does not have any new dependencies "
        "beyond the currently allowed ones."
    )
    rationale = (
        "The Base pack should not have dependencies. "
        "Currently it has 2 existing dependencies (Core and AggregateScripts) "
        "that are pending removal. No new dependencies should be added."
    )
    error_message = (
        "The Base pack should not have new dependencies. "
        "Found the following unexpected dependencies: {new_dependencies}. "
        "Only the following dependencies are currently allowed: "
        f"{', '.join(sorted(BASE_PACK_ALLOWED_DEPENDENCIES))}."
    )
    related_field = "dependencies"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        pack_ids = (
            [] if validate_all_files else [pack.object_id for pack in content_items]
        )

        # Only check the Base pack
        if pack_ids and BASE_PACK not in pack_ids:
            return validation_results

        base_pack_nodes = self.graph.search(
            content_type=ContentTypes.content_type,
            object_id=BASE_PACK,
        )
        for base_pack_node in base_pack_nodes:
            dependency_pack_ids = {
                relationship.content_item_to.object_id
                for relationship in base_pack_node.depends_on
                if not relationship.is_test
            }
            if new_deps := dependency_pack_ids - BASE_PACK_ALLOWED_DEPENDENCIES:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            new_dependencies=", ".join(sorted(new_deps))
                        ),
                        content_object=base_pack_node,
                    )
                )
        return validation_results
