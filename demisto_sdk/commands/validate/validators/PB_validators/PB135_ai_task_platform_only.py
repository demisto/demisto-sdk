from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class AITaskPlatformOnlyValidator(BaseValidator[ContentTypes]):
    error_code = "PB135"
    description = (
        "Ensure that playbooks with AI tasks are only supported "
        "in the platform marketplace."
    )
    rationale = (
        "AI tasks are a platform-specific feature and can only be executed "
        "in the platform marketplace. Playbooks containing AI tasks must "
        "restrict their marketplace support to 'platform' only."
    )
    error_message = (
        "The playbook contains AI tasks but is not restricted to the "
        "platform marketplace. Playbooks with AI tasks must have "
        "marketplaces set to ['platform'] in the pack_metadata.json. "
        "Found AI tasks in the following task IDs: {}"
    )
    related_field = "tasks"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []

        for content_item in content_items:
            ai_task_ids = self.find_ai_tasks(content_item)

            if ai_task_ids:
                # Check if the pack is restricted to platform marketplace
                pack_marketplaces = content_item.marketplaces

                if not pack_marketplaces or (
                    MarketplaceVersions.PLATFORM not in pack_marketplaces
                    or len(pack_marketplaces) > 1
                ):
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(", ".join(ai_task_ids)),
                            content_object=content_item,
                        )
                    )

        return validation_results

    def find_ai_tasks(self, content_item: ContentTypes) -> List[str]:
        """Find all AI tasks in the playbook.

        Args:
            content_item (ContentTypes): The playbook to check.

        Returns:
            List[str]: List of task IDs that are AI tasks.
        """
        ai_task_ids = []
        tasks = content_item.data.get("tasks", {})

        for task_id, task_config in tasks.items():
            task_type = task_config.get("type")
            # Check if the task type is aiTask
            if task_type == "aiTask":
                ai_task_ids.append(task_id)

        return ai_task_ids
