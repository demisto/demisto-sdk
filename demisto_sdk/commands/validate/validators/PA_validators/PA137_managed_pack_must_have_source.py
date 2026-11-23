from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class ManagedPackMustHaveSourceValidator(BaseValidator[ContentTypes]):
    error_code = "PA137"
    description = (
        "Validate that packs with 'managed: true' have a non-empty 'source' "
        "field in pack_metadata.json."
    )
    rationale = (
        "Managed packs must specify their source to maintain proper "
        "attribution and tracking in the managed content pipeline."
    )
    error_message = (
        "Pack '{0}' has 'managed: true' but is missing a non-empty 'source' "
        "field. Managed packs must specify their source."
    )
    related_field = "source"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(pack.object_id),
                content_object=pack,
            )
            for pack in content_items
            if pack.managed and not pack.source
        ]
