from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsTasksQuietModeValidator(BaseValidator[ContentTypes]):
    error_code = "PB115"
    description = "Checks if all tasks in a playbook are in quiet mode."
    error_message = "Playbook '{playbook_name}' contains tasks that are not in quiet mode (quietmode: 2)."
    fix_message = "Fixed playbook to set all tasks with (quietmode: 2) to (quietmode: 0)."
    related_field = "tasks"
    is_auto_fixable = True
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """
        Validates that tasks in content_items(playbook) are in quiet mode if they contain an input query for "indicators".

        Args:
            content_items (Iterable[ContentTypes]): Content items to validate.

        Returns:
            List[ValidationResult]: Validation results for items not meeting criteria.
        """
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                any(
                    (i.get("playbookInputQuery") or {}).get("queryEntity") == "indicators"
                    for i in content_item.data.get("inputs", {})
                )
                and [
                    task_key
                    for _, task_key in content_item.tasks.items()
                    if task_key.quietmode == 2
                ]
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Sets quietmode to 0 for all tasks with quietmode set to 2 in the given content item.

        Args:
            content_item (ContentTypes): The content item to fix.

        Returns:
            FixResult: The result of the fix operation.
        """
        for _, task_key in content_item.tasks.items():
            if task_key.quietmode == 2:
                task_key.quietmode = 0
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
