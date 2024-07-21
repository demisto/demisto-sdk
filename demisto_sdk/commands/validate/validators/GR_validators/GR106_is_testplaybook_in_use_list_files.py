
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook

from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

from demisto_sdk.commands.validate.validators.GR_validators.GR106_is_testplaybook_in_use import IsTestPlaybookInUseValidator

# ContentTypes = Union[Integration, Script, Playbook, TestPlaybook]


# class IsTestPlaybookInUseValidatorListFiles(IsTestPlaybookInUseValidator, BaseValidator[ContentTypes]):
#     expected_execution_mode = [ExecutionMode.ALL_FILES]

#     def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
#         return self.is_valid_using_graph(content_items, False)
        