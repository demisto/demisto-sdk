from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.common.constants import (
    INTEGRATION_FIELDS_NOT_ALLOWED_TO_CHANGE,
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsChangedOrRemovedFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "BC114"
    description = "Ensure a pre-defined list of fields wasn't removed or modified in the integration yml."
    rationale = "We wish to keep our behavior between different versions of the content item so we wish to enforce backwards compatibility breaking."
    error_message = "The following fields were modified/removed from the integration, please undo:\n{0}"
    related_field = "feed, isfetch, longRunning, longRunningPort, ismappable, isremotesyncin, isremotesyncout"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The following fields were {action}: {', '.join(fields)}."
                            for action, fields in altered_fields.items()
                            if fields
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (old_obj := content_item.old_base_content_object)
            and (old_obj_data := old_obj.data)  # type: ignore[attr-defined]
            and (
                altered_fields := self.obtain_removed_fields(
                    content_item.data.get("script", {}), old_obj_data.get("script", {})
                )
            )
        ]

    def obtain_removed_fields(
        self, current_data: dict, old_data: dict
    ) -> Dict[str, List[str]]:
        """Retrieve the modified and removed fields.

        Args:
            current_data (dict): The yml content script section after the modification.
            old_data (dict): The yml content script section before the modification.

        Returns:
            Dict[str, List[str]]: The modified and removed fields mapped.
        """
        removed_fields = []
        modified_fields = []
        for field in INTEGRATION_FIELDS_NOT_ALLOWED_TO_CHANGE:
            if old_field := old_data.get(field):
                if (current_field := current_data.get(field)) in [
                    True,
                    False,
                    "true",
                    "false",
                ]:
                    if current_field != old_field and current_field in [False, "false"]:
                        modified_fields.append(field)
                else:
                    removed_fields.append(field)
        if removed_fields or modified_fields:
            return {"removed": removed_fields, "modified": modified_fields}
        return {}
