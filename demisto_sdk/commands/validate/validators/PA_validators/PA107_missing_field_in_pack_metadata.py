from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PACK_METADATA_FIELDS
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class MissingFieldInPackMetadataValidator(BaseValidator[ContentTypes]):
    error_code = "PA107"
    description = "Ensure that mandatory fields exist in the pack_metadata."
    fix_message = "The following fields were added to the file as empty fields: {0}."
    error_message = "The following fields are missing from the file: {0}."
    related_field = "name, desc, support, currentVersion, author, url, categories, tags, useCases, keywords"
    is_auto_fixable = True

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
                    field for field in PACK_METADATA_FIELDS if field not in content_item.pack_metadata_dict  # type: ignore
                ]
            )
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        missing_fields = [
            field for field in PACK_METADATA_FIELDS if field not in content_item.pack_metadata_dict  # type: ignore
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(missing_fields)),
            content_object=content_item,
        )
