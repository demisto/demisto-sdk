from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class CouplingOverrideReferencesValidator(BaseValidator[ContentTypes]):
    error_code = "PA135"
    description = (
        "Validate that all keys in coupling_overrides reference valid "
        "content item IDs within the pack."
    )
    rationale = (
        "Coupling overrides that reference non-existent content items are "
        "silently ignored, which may lead to unexpected split-pack behavior."
    )
    error_message = (
        "Pack '{0}' has coupling_overrides referencing unknown content item "
        "IDs: {1}. These IDs do not match any content item in the pack."
    )
    related_field = "coupling_overrides"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for pack in content_items:
            overrides = pack.coupling_overrides
            if not overrides:
                continue
            pack_item_ids = {
                item.object_id for item in pack.content_items if item.object_id
            }
            unknown_ids = sorted(set(overrides.keys()) - pack_item_ids)
            if unknown_ids:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            pack.object_id, ", ".join(unknown_ids)
                        ),
                        content_object=pack,
                    )
                )
        return results
