from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.base_validator import (
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place import (
    MarketplacesFieldValidator,
)


class MarketplacesFieldValidatorListFiles(MarketplacesFieldValidator):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def obtain_invalid_content_items(
        self, content_items: Iterable
    ) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items)
