from __future__ import annotations

from abc import ABC
from collections import defaultdict
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsInvalidPacksDependenciesValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR108"
    description = "Validates that non-hidden packs do not have a hidden packs as mandatory dependencies."
    rationale = "Hidden packs are not available to install in the marketplace."
    error_message = "Pack {dependent_pack} has hidden pack(s) {hidden_packs} in its mandatory dependencies"
    related_field = "dependencies"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        pack_ids = (
            [] if validate_all_files else [pack.object_id for pack in content_items]
        )

        # Find packs with dependencies on hidden packs
        packs_with_invalid_dependencies = (
            self.graph.find_packs_with_invalid_dependencies(pack_ids=pack_ids)
        )
        dependent_pack_to_hidden_packs = defaultdict(set)

        # Collect hidden pack dependencies for each dependent pack
        for dependent_pack in packs_with_invalid_dependencies:
            for dependency in dependent_pack.depends_on:
                hidden_pack = dependency.content_item_to
                dependent_pack_to_hidden_packs[dependent_pack].add(
                    hidden_pack.object_id
                )

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    dependent_pack=dependent_pack.object_id,
                    hidden_packs=", ".join(hidden_pack_ids),
                ),
                content_object=dependent_pack,
            )
            for dependent_pack, hidden_pack_ids in dependent_pack_to_hidden_packs.items()
        ]
