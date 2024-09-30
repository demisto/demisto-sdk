
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
    error_code = "GR999"
    description = ""
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False


    def obtain_invalid_content_items_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        mp_to_core_packs = get_marketplace_to_core_packs()
        for marketplace, mp_core_packs in mp_to_core_packs.items():
            if not self.pack_ids:
                pack_ids_to_check = list(mp_core_packs)
            else:
                pack_ids_to_check = [
                    pack_id for pack_id in self.pack_ids if pack_id in mp_core_packs
                ]

            for core_pack_node in self.graph.find_core_packs_depend_on_non_core_packs(
                pack_ids_to_check, marketplace, list(mp_core_packs)
            ):
                non_core_pack_dependencies = [
                    relationship.content_item_to.object_id
                    for relationship in core_pack_node.depends_on
                    if not relationship.is_test
                ]
                error_message, error_code = Errors.invalid_core_pack_dependencies(
                    core_pack_node.object_id, non_core_pack_dependencies
                )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        

    
