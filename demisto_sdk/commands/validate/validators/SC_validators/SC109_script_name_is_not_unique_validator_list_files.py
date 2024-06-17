from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator import (
    DuplicatedScriptNameValidator,
)

ContentTypes = Script


class DuplicatedScriptNameValidatorListFiles(
    DuplicatedScriptNameValidator, BaseValidator[ContentTypes]
):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return self.is_valid_using_graph(
            content_items=content_items, validate_all_files=False
        )
