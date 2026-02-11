from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.AS_validators.AS102_is_valid_autonomous_playbook_dependencies import (
    IsValidAutonomousPlaybookDependenciesValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ValidationResult,
)


class IsValidAutonomousPlaybookDependenciesValidatorAllFiles(
    IsValidAutonomousPlaybookDependenciesValidator,
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(
            content_items, validate_all_files=True
        )
