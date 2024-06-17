from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


def is_indicator_pb(playbook: Playbook):
    return any(
        (i.get("playbookInputQuery") or {}).get("queryEntity") == "indicators" for i in playbook.data.get("inputs", {})
    )


def does_playbook_continue_on_error(playbook: Playbook):
    return any(task.continueonerror for task in playbook.tasks.values())


class IsStoppingOnErrorValidator(BaseValidator[ContentTypes]):
    error_code = "PB116"
    description = "The validation checks that all playbook tasks stop when encountering an error."
    rationale = "If a playbook task does not stop on error, following tasks might rely on its output and fail."
    error_message = "The following tasks of the playbook do not stop on error:\n{}"
    related_field = "tasks"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if is_indicator_pb(content_item) and does_playbook_continue_on_error(content_item)
        ]
