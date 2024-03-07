from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import MANDATORY_PACK_METADATA_FIELDS
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
    rationale = (
        "Missing these fields may lead to unexpected behavior when uploading the packs."
    )
    fix_message = "The following fields were added to the file as empty fields: {0}."
    error_message = "The following fields are missing from the file: {0}."
    related_field = "name, desc, support, currentVersion, author, url, categories, tags, useCases, keywords"
    is_auto_fixable = True
    missing_fields: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(missing_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (missing_fields := self.get_missing_fields(content_item))
        ]

    def get_missing_fields(self, content_item: ContentTypes) -> List[str]:
        """Extract the list of missing fields from the metadata file.

        Args:
            content_item (ContentTypes): the pack_metadata object.

        Returns:
            List[str]: the list of missing fields.
        """
        if missing_fields := [field for field in MANDATORY_PACK_METADATA_FIELDS if field not in content_item.pack_metadata_dict]:  # type: ignore[operator]
            self.missing_fields[content_item.name] = missing_fields
        return missing_fields

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        # By adding the contentItem as a fix result, when we attempt to save fields into the contentItem, we'll make sure to add the missing fields as a part of Pack object save method
        missing_fields = self.missing_fields[content_item.name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(missing_fields)),
            content_object=content_item,
        )
