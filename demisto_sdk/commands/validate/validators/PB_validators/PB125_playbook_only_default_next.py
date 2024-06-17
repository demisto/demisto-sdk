from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookOnlyDefaultNextValidator(BaseValidator[ContentTypes]):
    error_code = "PB125"
    description = (
        "Validates that a condition task doesn't has only a default next-task."
    )
    rationale = "Validates that a condition task doesn't has only a default next-task."
    error_message = (
        'Playbook with id:"{playbook_id}" has conditional tasks with an only default condition. Tasks IDs: {tasks}.\n'
        "Please remove these tasks or add another non-default condition to these conditional tasks"
    )
    related_field = "conditions"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        tasks_with_only_default_nexttasks: dict = dict()

        for content_item in content_items:
            for task_id, task in content_item.tasks.items():
                if (
                    len(list(task.nexttasks or {})) == 1
                    and list((task.nexttasks or {}).keys())[0].lower() == "#default#"
                ):
                    tasks_with_only_default_nexttasks.setdefault(
                        content_item.object_id, []
                    ).append(task_id)

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(playbook_id=playbook_id, tasks=tasks),
                content_object=content_item,
            )
            for playbook_id, tasks in tasks_with_only_default_nexttasks.items()
        ]
