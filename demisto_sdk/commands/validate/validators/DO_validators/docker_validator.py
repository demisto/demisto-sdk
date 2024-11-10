from __future__ import annotations

from abc import ABC
from typing import Optional

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ContentTypes,
)


class DockerValidator(BaseValidator[ContentTypes], ABC):
    def should_run(
        self,
        content_item: ContentTypes,
        ignorable_errors: list,
        support_level_dict: dict,
        running_execution_mode: Optional[ExecutionMode],
    ) -> bool:
        return "apimodule" not in (
            str(content_item.path)
        ).lower() and super().should_run(
            content_item, ignorable_errors, support_level_dict, running_execution_mode
        )
