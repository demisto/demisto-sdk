from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.base_validator import (
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR103_is_using_unknown_content import (
    ContentTypes,
    IsUsingUnknownContentValidator,
)


class IsUsingUnknownContentValidatorListFiles(IsUsingUnknownContentValidator):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items)
