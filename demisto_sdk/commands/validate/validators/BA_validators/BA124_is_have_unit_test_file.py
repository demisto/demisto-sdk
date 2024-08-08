from __future__ import annotations

from pathlib import Path
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
    error_message = "The given {0} is missing a unit test file, please make sure to add one with the following name {1}."
    related_field = "test"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.path.name.replace(".yml", "_test.py"),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.support in [PARTNER_SUPPORT, XSOAR_SUPPORT]
                and content_item.type == TYPE_PYTHON
                and content_item.path.with_name(f"{content_item.path.stem}.py").exists()
                and not self.case_sensitive_exists(
                    content_item.path.with_name(f"{content_item.path.stem}_test.py")
                )
            )
        ]

    def case_sensitive_exists(self, unit_test_path: Path) -> bool:
        """Checks if the unit test file's path (case sensitive) exists.

        Args:
            unit_test_path (Path): The unit test file's path to check.

        Returns:
            bool: If the path exists, taking into consideration case sensitivity.
        """
        if not unit_test_path.exists():
            return False
        # Checking if the file exists is not enough since Path.exists() isn't always case sensitive (related to file system configuration)
        # List all file names in the directory of the given path
        actual_files = [file.name for file in unit_test_path.parent.iterdir()]
        # Check if the exact file name exists in the directory
        return unit_test_path.name in actual_files
