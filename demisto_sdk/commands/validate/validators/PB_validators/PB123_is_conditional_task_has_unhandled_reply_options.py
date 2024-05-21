from __future__ import annotations

from typing import Iterable, List

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


class IsAskConditionHasUnhandledReplyOptionsValidator(BaseValidator[ContentTypes]):
    error_code = "PB123"
    description = "Checks whether an ask conditional has unhandled reply options."
    rationale = "Checks whether an ask conditional has unhandled reply options."
    error_message = (
        "Playbook conditional task with id:{task_id} has an unhandled "
        "condition: {condition}."
    )
    related_field = "conditions"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """Checks whether a builtin conditional task branches are handled properly
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = self.unhandled_conditions(content_item)

            for task_id, unhandled_options in invalid_tasks.items():
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            task_id=task_id,
                            condition=",".join(
                                map(lambda x: f"{str(x)}", unhandled_options)
                            ),
                        ),
                        content_object=content_item,
                    )
                )

        return results

    @staticmethod
    def unhandled_conditions(playbook: ContentTypes):
        unhandled_conditions = {}
        tasks = playbook.tasks
        for task in tasks.values():
            if task.get("type") == "condition" and task.get("message"):
                next_tasks: dict = task.get("nexttasks", {})

                # ADD all replyOptions to unhandled_reply_options (UPPER)
                unhandled_reply_options = set(
                    map(str.upper, task.get("message", {}).get("replyOptions", []))
                )

                # Rename the keys in dictionary to upper case
                next_tasks_upper = {k.upper(): v for k, v in next_tasks.items()}

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

                if unhandled_reply_options:
                    # if there's only one unhandled_reply_options and there's a #default#
                    # then all good.
                    # Otherwise - Error
                    if not (
                        len(unhandled_reply_options) == 1
                        and "#DEFAULT#" in next_tasks_upper
                    ):
                        unhandled_conditions[task.get("id")] = unhandled_reply_options

        return unhandled_conditions
