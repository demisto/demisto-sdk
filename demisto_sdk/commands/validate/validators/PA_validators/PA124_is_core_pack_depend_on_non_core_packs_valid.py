from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_marketplace_to_core_packs
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsCorePackDependOnNonCorePacksValidator(BaseValidator[ContentTypes], ABC):
    error_code = "PA124"
    description = "Validates that core packs do not depend on non-core packs."
    rationale = "Core packs should be self-contained."
    error_message = "The core pack {core_pack} cannot depend on non-core pack(s): {dependencies_packs}."
    related_field = "dependencies"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_results = []
        pack_ids = (
            [] if validate_all_files else [pack.object_id for pack in content_items]
        )
        mp_to_core_packs = get_marketplace_to_core_packs()
        for marketplace, mp_core_packs in mp_to_core_packs.items():
            pack_ids_to_check = (
                list(mp_core_packs)
                if not pack_ids
                else list(set(pack_ids).intersection(mp_core_packs))
            )
            for core_pack_node in self.graph.find_core_packs_depend_on_non_core_packs(
                pack_ids_to_check, marketplace, list(mp_core_packs)
            ):
                non_core_pack_dependencies = [
                    relationship.content_item_to.object_id
                    for relationship in core_pack_node.depends_on
                ]

                if non_core_pack_dependencies:
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                core_pack=core_pack_node.object_id,
                                dependencies_packs=", ".join(
                                    non_core_pack_dependencies
                                ),
                            ),
                            content_object=core_pack_node,
                        )
                    )
        return validation_results
