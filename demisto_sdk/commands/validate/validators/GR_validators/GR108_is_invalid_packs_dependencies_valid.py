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
    description = (
        "Validates that hidden packs are not mandatory dependencies for other packs."
    )
    rationale = "Hidden packs should not be critical dependencies to ensure proper pack management."
    error_message = "Pack {dependent_pack} depends on hidden pack(s): {hidden_packs}"
    related_field = "dependencies"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        pack_ids = (
            [] if validate_all_files else [pack.object_id for pack in content_items]
        )
        validation_results = []
        dependent_packs = self.graph.find_invalid_pack_dependencies(pack_ids=pack_ids)
        pack_to_hidden_packs = defaultdict(set)

        for pack in dependent_packs:
            for relationship in pack.depends_on:
                hidden_pack = relationship.content_item_to
                pack_to_hidden_packs[pack].add(hidden_pack.object_id)

        for dependent_pack, hidden_pack_ids in pack_to_hidden_packs.items():
            error_message = self.error_message.format(
                dependent_pack=dependent_pack.object_id,
                hidden_packs=", ".join(hidden_pack_ids),
            )
            validation_results.append(
                ValidationResult(
                    validator=self,
                    message=error_message,
                    content_object=dependent_pack,
                )
            )

        return validation_results
