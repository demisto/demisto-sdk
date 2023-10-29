from typing import Iterable, List, Optional, Union, cast

from demisto_sdk.commands.common.constants import ADDED, MODIFIED
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixingResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class BCSubtypeValidator(BaseValidator[ContentTypes]):
    error_code = "BC100"
    description = (
        "Validate that the pack name subtype of the new file matches the old one."
    )
    error_message = "Possible backwards compatibility break, You've changed the subtype, please undo."
    is_auto_fixable = True
    related_field = "subtype"
    fixing_message = "Changing subtype back to the old one ({0})."
    expected_git_statuses = [ADDED, MODIFIED]

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
        old_content_items: Iterable[Optional[ContentTypes]],
    ) -> List[ValidationResult]:
        old_content_items = cast(Iterable[ContentTypes], old_content_items)
        validation_results = []
        for content_item, old_content_item in zip(content_items, old_content_items):
            if content_item.type != old_content_item.type:
                validation_results.append(
                    ValidationResult(
                        content_object=content_item,
                        old_content_object=old_content_item,
                        is_valid=False,
                        message=self.error_message.format(content_item.name),
                        validator=self,
                    )
                )
        return validation_results

    def fix(
        self, content_item: ContentTypes, old_content_item: ContentTypes
    ) -> FixingResult:
        content_item.type = old_content_item.type
        content_item.save()
        return FixingResult(
            validator=self,
            message=self.fixing_message.format(old_content_item.type),
            content_object=content_item,
        )
