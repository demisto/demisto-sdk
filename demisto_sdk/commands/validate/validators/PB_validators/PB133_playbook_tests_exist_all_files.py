from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult
from demisto_sdk.commands.validate.validators.PB_validators.PB133_playbook_tests_exist import (
    PlaybookTestsExistValidator,
)

ContentTypes = Playbook


class PlaybookTestsExistValidatorAllFiles(PlaybookTestsExistValidator):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, True)
