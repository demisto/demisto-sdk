from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version import (
    IsUsingInvalidFromVersionValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version_list_files import (
    ContentTypes,
)


class IsUsingInvalidFromVersionValidatorAllFiles(
    IsUsingInvalidFromVersionValidator, BaseValidator[ContentTypes]
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph([], True)
