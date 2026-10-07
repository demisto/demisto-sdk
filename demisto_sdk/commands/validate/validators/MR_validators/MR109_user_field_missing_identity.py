from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_TO_VERSION
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class UserFieldMissingIdentityValidator(BaseValidator[ContentTypes]):
    error_code = "MR109"
    description = (
        "Validates that every xdm.*.user.* field in a modeling rule has a "
        "corresponding xdm.*.identity.* field."
    )
    rationale = (
        "User and Identity XDM fields are correlated - for each xdm.*.user.* field "
        "the matching xdm.*.identity.* field must also be mapped."
    )
    error_message = (
        "The following xdm.*.user.* fields are missing their corresponding "
        "xdm.*.identity.* field: {missing_fields}."
    )
    related_field = "XIF"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.XIF]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.toversion != DEFAULT_CONTENT_ITEM_TO_VERSION:
                continue
            field_counts = content_item.xif_file.get_user_identity_fields()
            missing = sorted(
                field
                for field, user_count in field_counts.items()
                if ".user." in field
                and field_counts[field.replace(".user.", ".identity.", 1)] < user_count
            )
            if missing:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            missing_fields=", ".join(missing)
                        ),
                        content_object=content_item,
                        path=content_item.xif_file.file_path,
                    )
                )
        return results
