from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

GENERIC_FIELD_ID_PREFIX = "generic_"
ContentTypes = GenericField


class GenericFieldIdPrefixValidateValidator(BaseValidator[ContentTypes]):
    error_code = "GF101"
    rationale = "Required by the platform."
    description = "Checks if the id starts with `generic_`."
    error_message = (
        "{generic_id} is not a valid id, it should start with {generic_id_prefix}."
    )
    related_field = "id"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
