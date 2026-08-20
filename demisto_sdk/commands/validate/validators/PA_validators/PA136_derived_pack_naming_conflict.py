from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.common import DERIVED_PACK_SUFFIX
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class DerivedPackNamingConflictValidator(BaseValidator[ContentTypes]):
    error_code = "PA136"
    description = (
        "Validate that the derived pack ID (pack_id + 'Managed') does not "
        "collide with an existing pack in the repository."
    )
    rationale = (
        "When the SDK generates a derived pack for a split-pack candidate, "
        "the derived pack ID is formed by appending 'Managed' to the "
        "original pack ID. If another pack already has that ID, the build "
        "will fail with a naming collision."
    )
    error_message = (
        "Pack '{0}' would generate a derived pack with ID '{1}', but a pack "
        "with that ID already exists. Rename one of the packs to avoid the "
        "collision."
    )
    related_field = "name"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        # Collect all pack IDs first
        all_packs = list(content_items)
        all_pack_ids = {pack.object_id for pack in all_packs}

        results: List[ValidationResult] = []
        for pack in all_packs:
            # Only check non-managed, non-derived packs that could generate
            # a derived pack
            if pack.managed or getattr(pack, "is_derived", False):
                continue
            derived_id = f"{pack.object_id}{DERIVED_PACK_SUFFIX}"
            if derived_id in all_pack_ids:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            pack.object_id, derived_id
                        ),
                        content_object=pack,
                    )
                )
        return results
