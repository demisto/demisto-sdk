from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.AG_validators.AG116_agent_includes_skill_action_dependencies import (
    IsAgentIncludesSkillActionDependenciesValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ValidationResult,
)


class IsAgentIncludesSkillActionDependenciesValidatorAllFiles(
    IsAgentIncludesSkillActionDependenciesValidator
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph([], True)
