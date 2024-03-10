from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    PARTNER_SUPPORT,
    TYPE_PYTHON,
    XSOAR_SUPPORT,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsHaveUnitTestFileValidator(BaseValidator[ContentTypes]):
    error_code = "BA124"
    description = "Validate that the script / integration has a unit test file."
    rationale = "Unit tests make sure that the behaviors in code are consistent between versions."
    error_message = "The given {0} is missing a unit test file, please make sure to add one with the following name {2}."
    related_field = "test"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    str(content_item.path).replace("yml", "_test.py"),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.support_level in [PARTNER_SUPPORT, XSOAR_SUPPORT]
                and content_item.type == TYPE_PYTHON
                and content_item.path.with_name(f"{content_item.path.stem}.py").exists()
                and not content_item.path.with_name(
                    f"{content_item.path.stem}_test.py"
                ).exists()
            )
        ]
