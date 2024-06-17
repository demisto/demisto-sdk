from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Playbook, TestPlaybook]


class IsPlayBookUsingAnInstanceValidator(BaseValidator[ContentTypes]):
    error_code = "PB106"
    description = "Validate whether the playbook does not use an instance. If the Playbook use an instance it is not valid."
    rationale = "If the playbook uses a specific instance it can leads to errors because not all the users have the same instance"
    error_message = "Playbook should not use specific instance."
    fix_message = "The using instance from the playbook was removed"
    related_field = ""
    is_auto_fixable = True
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
    ]
    related_file_type = [RelatedFileType.YML]

    @staticmethod
    def is_playbook_using_an_instance(
        content_item_tasks: dict[str, TaskConfig]
    ) -> bool:
        for _, task in content_item_tasks.items():
            scriptargs = task.scriptarguments
            if scriptargs and scriptargs.get("using", {}):
                return True
        return False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (self.is_playbook_using_an_instance(content_item.tasks))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        tasks: dict[str, TaskConfig] = content_item.tasks
        for _, task in tasks.items():
            scriptargs = task.scriptarguments
            if scriptargs and scriptargs.get("using", {}):
                scriptargs.pop("using")
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
