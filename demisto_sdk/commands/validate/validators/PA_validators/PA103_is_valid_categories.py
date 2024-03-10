from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import API_MODULES_PACK
from demisto_sdk.commands.common.tools import get_current_categories
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.tools import validate_categories_approved
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidCategoriesValidator(BaseValidator[ContentTypes]):
    error_code = "PA103"
    description = "Validate that the pack categories are valid."
    rationale = (
        "See the list of allowed categories in the platform: "
        "https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The pack metadata categories field doesn't match the standard,\nplease make sure the field contain only one category from the following options: {0}."
    related_field = "categories"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        approved_list = get_current_categories()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(approved_list)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                len(content_item.categories) != 1  # type:ignore[arg-type]
                or not validate_categories_approved(
                    content_item.pack_metadata_dict.get("categories", []), approved_list  # type: ignore[union-attr]
                )
            )
            and content_item.name != API_MODULES_PACK
        ]
