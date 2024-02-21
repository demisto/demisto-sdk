from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

GENERIC_FIELD_ID_PREFIX = "generic_"
ContentTypes = GenericField


class GenericFieldIdPrefixValidateValidator(BaseValidator[ContentTypes]):
    error_code = "GF101"
    description = "Validate the id field include prefix `generic_`"
    error_message = "ID {generic_id} is not a valid generic field ID - it should start with the prefix {generic_id_prefix}."
    fix_message = ""
    related_field = "id"
    is_auto_fixable = True
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    generic_id=content_item.object_id,
                    generic_id_prefix=GENERIC_FIELD_ID_PREFIX,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.object_id.startswith(GENERIC_FIELD_ID_PREFIX))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.object_id = GENERIC_FIELD_ID_PREFIX + content_item.object_id
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item),
            content_object=content_item,
        )
