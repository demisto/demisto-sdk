from __future__ import annotations

from typing import ClassVar, Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsPriceChangedValidator(BaseValidator[ContentTypes]):
    error_code = "PA121"
    description = "Validate that no changes were done to the pack's price."
    rationale = "Changing this field affects paying customer. In the demisto/content repo, this requires a force-merge."
    error_message = "The pack price was changed from {0} to {1} - revert the change."
    fix_message = "Reverted the price back to {0}."
    related_field = "price"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]
    old_prices_dict: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.old_prices_dict[content_item.name] or "not included",
                    content_item.price or "not included",
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_price_changed(content_item)
        ]

    def is_price_changed(self, content_item: ContentTypes) -> bool:
        """Check if the price changed for a given metadata file and update the `old_prices_dict` accordingly.

        Args:
            content_item (ContentTypes): The metadata object.

        Returns:
            bool: Wether the price was changed or not.
        """
        old_obj = cast(ContentTypes, content_item.old_base_content_object)
        is_price_changed: bool = (
            (content_item.price and not old_obj.price)  # type: ignore[assignment]
            or (not content_item.price and old_obj.price)
            or content_item.price != old_obj.price
        )
        if is_price_changed:
            self.old_prices_dict[content_item.name] = old_obj.price
        return is_price_changed

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.price = self.old_prices_dict[content_item.name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.price),
            content_object=content_item,
        )
