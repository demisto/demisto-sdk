from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult
from demisto_sdk.commands.validate.validators.GR_validators.GR108_is_invalid_packs_dependencies_valid import (
    IsInvalidPacksDependenciesValidator,
)

ContentTypes = Pack


class IsInvalidPacksDependenciesValidatorAllFiles(IsInvalidPacksDependenciesValidator):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, True)
