from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook

MAPPER_DICT = {
    "YES": ["YES", "TRUE POSITIVE"],
    "TRUE POSITIVE": ["YES", "TRUE POSITIVE"],
    "NO": ["NO", "FALSE POSITIVE"],
    "FALSE POSITIVE": ["NO", "FALSE POSITIVE"],
}


class IsAskConditionHasUnreachableConditionValidator(BaseValidator[ContentTypes]):
    error_code = "PB101"
    description = "Checks whether an ask conditional has task with unreachable next task condition."
    rationale = "Checks whether an ask conditional has task with unreachable next task condition."
    error_message = (
        "Playbook conditional task with id:{task_id} has task with unreachable "
        "next task condition '{next_task_branch}'. Please remove this task or add "
        "this condition to condition task with id:{task_id}."
    )
    related_field = "tasks"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Checks whether a builtin conditional task branches are handled properly
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = self.invalid_tasks(content_item)

            for task_id, next_task_branch in invalid_tasks.items():
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            task_id=task_id,
                            next_task_branch=next_task_branch,
                        ),
                        content_object=content_item,
                    )
                )

        return results

    @staticmethod
    def invalid_tasks(playbook: ContentTypes):
        invalid_tasks = {}
        tasks = playbook.tasks
        for task in tasks.values():
            if task.type == PlaybookTaskType.CONDITION and task.message:
                next_tasks: dict = task.nexttasks or {}
                # Rename the keys in dictionary to upper case
                next_tasks_upper = {k.upper(): v for k, v in next_tasks.items()}

                # ADD all replyOptions to unhandled_reply_options (UPPER)
                unhandled_reply_options = set(
                    map(str.upper, task.message.get("replyOptions", []))
                )

                # Remove all nexttasks from unhandled_reply_options (UPPER)
                for next_task_branch, next_task_id in next_tasks_upper.items():
                    key_to_remove = None
                    if next_task_id and next_task_branch != "#DEFAULT#":
                        for mapping in MAPPER_DICT.get(
                            next_task_branch, [next_task_branch]
                        ):
                            if mapping in unhandled_reply_options:
                                key_to_remove = mapping
                        if key_to_remove:
                            unhandled_reply_options.remove(key_to_remove)
                        else:
                            invalid_tasks[task.id] = next_task_branch

        return invalid_tasks
