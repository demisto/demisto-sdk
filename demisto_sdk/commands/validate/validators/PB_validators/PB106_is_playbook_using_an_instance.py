from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsPlayBookUsingAnInstanceValidator(BaseValidator[ContentTypes]):
    invalid_tasks: ClassVar[dict] = {}
    error_code = "PB106"
    description = "Validate whether the playbook does not use an instance. If the Playbook use an instance it is not valid."
    rationale = "If the playbook uses a specific instance it can leads to errors because not all the users have the same instance."
    error_message = "Playbook should not use specific instance for tasks: {0}."
    fix_message = "Removed The 'using' statement from the following tasks tasks: {0}."
    related_field = "using"
    is_auto_fixable = True

    def is_playbook_using_an_instance(
        self, content_item: ContentTypes
    ) -> list[TaskConfig]:
        content_item_tasks: Dict[str, TaskConfig] = content_item.tasks
        invalid_tasks: list[TaskConfig] = []
        for _, task in content_item_tasks.items():
            scriptargs = task.scriptarguments
            if scriptargs and scriptargs.get("using"):
                invalid_tasks.append(task)
        self.invalid_tasks[content_item.name] = invalid_tasks
        return invalid_tasks

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join([task.taskid for task in invalid_tasks])
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_tasks := self.is_playbook_using_an_instance(content_item))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        invalid_tasks = self.invalid_tasks[content_item.name]
        for invalid_task in invalid_tasks:
            scriptargs = invalid_task.scriptarguments
            if scriptargs and scriptargs.get("using", {}):
                scriptargs.pop("using")
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join([task.taskid for task in invalid_tasks])
            ),
            content_object=content_item,
        )
