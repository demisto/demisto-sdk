from typing import ClassVar, Iterable, List, Union, cast

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
    rationale = (
        "Changing 'subtype' can break backward compatibility. "
        "For 'subtype' info, see: https://xsoar.pan.dev/docs/integrations/yaml-file#script"
    )
    error_message = "Possible backwards compatibility break, You've changed the {0} subtype from {1} to {2}, please undo."
    related_field = "subtype"
    fix_message = "Changing subtype back to ({0})."
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]
    is_auto_fixable = True
    old_subtype: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    self.old_subtype[content_item.name],
                    content_item.subtype,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_subtype_changed(content_item)
        ]

    def is_subtype_changed(self, content_item: ContentTypes) -> bool:
        """Check if the subtype was changed for a given metadata file and update the `old_subtype` accordingly.

        Args:
            content_item (ContentTypes): The metadata object.

        Returns:
            bool: Wether the subtype was changed or not.
        """
        old_obj = cast(ContentTypes, content_item.old_base_content_object)
        is_subtype_changed = (
            content_item.type == "python" and content_item.subtype != old_obj.subtype
        )
        if is_subtype_changed:
            self.old_subtype[content_item.name] = old_obj.subtype
        return is_subtype_changed

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.subtype = self.old_subtype[content_item.name]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.subtype),
            content_object=content_item,
        )
