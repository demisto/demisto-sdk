from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PACK_METADATA_MANDATORY_FILLED_FIELDS
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class EmptyMetadataFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "PA111"
    description = "Validate that certain metadata fields are not empty."
    rationale = (
        "'keywords', 'tags', 'categories', and 'useCases' fields in the pack metadata are mandatory for pack identification and searchability. "
        "For more info, see: https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The following fields contains empty values: {0}."
    related_field = "keywords, tags, categories, useCases"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(missing_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                missing_fields := [
                    field
                    for field in PACK_METADATA_MANDATORY_FILLED_FIELDS
                    if field in content_item.pack_metadata_dict  # type:ignore[operator]
                    and (
                        field_val := content_item.pack_metadata_dict[
                            field
                        ]  # type:ignore[index]
                    )  # type:ignore[index]
                    and "" in field_val
                ]
            )
        ]
