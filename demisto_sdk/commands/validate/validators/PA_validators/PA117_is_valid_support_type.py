from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PACK_SUPPORT_OPTIONS
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidSupportTypeValidator(BaseValidator[ContentTypes]):
    error_code = "PA117"
    description = "Validate that the pack's support type is a valid support type."
    rationale = "For valid support levels, see https://xsoar.pan.dev/docs/packs/packs-format#pack_metadatajson."
    error_message = "The pack's support type ({0}) is invalid.\nThe pack support type can only be one of the following {1}."
    related_field = "support"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.support, ", ".join(PACK_SUPPORT_OPTIONS)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.support not in PACK_SUPPORT_OPTIONS
        ]
