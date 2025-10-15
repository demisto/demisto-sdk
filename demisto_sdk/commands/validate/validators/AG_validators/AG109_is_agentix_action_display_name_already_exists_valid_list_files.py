from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.AG_validators.AG109_is_agentix_action_display_name_already_exists_valid import \
    IsAgentixActionDisplayNameAlreadyExistsValidator
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult


ContentTypes = Integration


class IsAgentixActionDisplayNameAlreadyExistsValidatorListFiles(
    IsAgentixActionDisplayNameAlreadyExistsValidator
):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, False)
