from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR103_is_using_unknown_content import (
    ContentTypes,
    IsUsingUnknownContentValidator,
)


class IsUsingUnknownContentValidatorAllFiles(
    IsUsingUnknownContentValidator, BaseValidator[ContentTypes]
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph([], True)
