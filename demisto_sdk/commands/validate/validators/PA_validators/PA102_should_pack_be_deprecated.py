from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class ShouldPackBeDeprecatedValidator(BaseValidator[ContentTypes]):
    error_code = "PA102"
    description = "Validate that the pack is deprecated if it needs to."
    rationale = (
        "This ensures clarity for users and prevents potential confusion of deprecated content. "
        "For more about deprecation see: https://xsoar.pan.dev/docs/reference/articles/deprecation-process-and-hidden-packs"
    )
    error_message = f"The Pack {0} should be deprecated, as all its integrations, playbooks and scripts are deprecated.\nThe name of the pack in the pack_metadata.json should end with (Deprecated).\nThe description of the pack in the pack_metadata.json should be one of the following formats:\n1. 'Deprecated. Use <PACK_NAME> instead.'\n2. 'Deprecated. <REASON> No available replacement.'"
    fix_message = "Deprecated the pack {0}.\nPlease make sure to edit the description of the pack in the pack_metadata.json file if there's an existing pack to use instead or add the deprecation reason."
    related_field = "deprecated"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.deprecated
            and self.are_all_content_items_deprecated(content_item)
        ]

    def are_all_content_items_deprecated(self, content_item: ContentTypes) -> bool:
        for integration in content_item.content_items.integration:
            if not integration.deprecated:
                return False
        for script in content_item.content_items.script:
            if not script.deprecated:
                return False
        for playbook in content_item.content_items.playbook:
            if not playbook.deprecated:
                return False
        return True

    def fix(self, content_item: ContentTypes) -> FixResult:
        if not content_item.name.endswith("(Deprecated)"):
            content_item.name = f"{content_item} (Deprecated)"
        content_item.description = "Deprecated. <REASON> No available replacement."
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.name),
            content_object=content_item,
        )
