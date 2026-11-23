from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult
from demisto_sdk.commands.validate.validators.GR_validators.GR112_is_agentix_action_name_already_exists_valid import (
    IsAgentixActionNameAlreadyExistsValidator,
)

ContentTypes = AgentixAction


class IsAgentixActionNameAlreadyExistsValidatorAllFiles(
    IsAgentixActionNameAlreadyExistsValidator
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, True)
