from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult
from demisto_sdk.commands.validate.validators.PA_validators.PA133_is_base_pack_has_no_new_dependencies import (
    IsBasePackHasNoNewDependenciesValidator,
)

ContentTypes = Pack


class IsBasePackHasNoNewDependenciesValidatorListFiles(
    IsBasePackHasNoNewDependenciesValidator
):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, False)
