from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PACK_METADATA_FIELDS
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class MissingFieldInPackMetadataValidator(BaseValidator[ContentTypes]):
    error_code = "PA107"
    description = "The following fields are missing from the file: {0}"
    error_message = ""
    fix_message = ""
    related_field = ""
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(missing_fields),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                missing_fields := [
                    field for field in PACK_METADATA_FIELDS if field not in content_item.pack_metadata_dict  # type: ignore
                ]
            )
        ]
