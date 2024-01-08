from typing import Iterable, List, Union, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class BreakingBackwardsSubtypeValidator(BaseValidator[ContentTypes]):
    error_code = "BC100"
    description = (
        "Validate that the pack name subtype of the new file matches the old one."
    )
    error_message = "Possible backwards compatibility break, You've changed the subtype, please undo."
    related_field = "subtype"
    fix_message = "Changing subtype back to the old one ({0})."
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    is_auto_fixable = True

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            old_obj = cast(ContentTypes, content_item.old_base_content_object)
            if (
                content_item.type == "python"
                and content_item.subtype != old_obj.subtype
            ):
                validation_results.append(
                    ValidationResult(
                        content_object=content_item,
                        message=self.error_message.format(content_item.name),
                        validator=self,
                    )
                )
        return validation_results

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        old_content_object = cast(ContentTypes, content_item.old_base_content_object)
        content_item.subtype = old_content_object.subtype
        return FixResult(
            validator=self,
            message=self.fix_message.format(old_content_object.subtype),
            content_object=content_item,
        )
