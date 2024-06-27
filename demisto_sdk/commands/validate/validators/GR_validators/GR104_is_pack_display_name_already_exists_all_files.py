from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists import (
    IsPackDisplayNameAlreadyExistsValidator,
)

ContentTypes = Pack


class IsPackDisplayNameAlreadyExistsValidatorAllFiles(
    IsPackDisplayNameAlreadyExistsValidator, BaseValidator[ContentTypes]
):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return self.is_valid_using_graph(
            content_items=content_items, validate_all_files=True
        )
