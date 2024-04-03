from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import get_files_in_dir
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]
ENTITY_NAME_SEPARATORS = [" ", "_", "-"]


class FileNameHasSeparatorsValidator(BaseValidator[ContentTypes]):
    error_code = "BA109"
    description = "Check if there are separators in the script or integration files names."
    rationale = ""
    error_message = (
        "The {0} files {1} should be named {2}, respectively, without any separators in the base name."
    )
    related_field = ""
    is_auto_fixable = False
    files_name_for_error_message: list[str] = []

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    ' and '.join([f"'{word}'" for word in self.files_name_for_error_message[1]]),
                    ' and '.join([f"'{word}'" for word in self.files_name_for_error_message[0]]),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (self.check_separators_in_files(content_item))
        ]

    def check_separators_in_files(self, content_item):
        invalid_files = []
        valid_files = []

        files_to_check = get_files_in_dir(
            os.path.dirname(content_item.path), ["yml", "py", "md", "png"], False
        )

        for file_path in files_to_check:
            if (file_name := Path(file_path).name).startswith("README"):
                continue

            if (
                file_name.endswith("_image.png")
                or file_name.endswith("_description.md")
                or file_name.endswith("_test.py")
                or file_name.endswith("_unified.yml")
            ):
                base_name = file_name.rsplit("_", 1)[0]
            else:
                base_name = file_name.rsplit(".", 1)[0]

            valid_base_name = self.remove_separators_from_name(base_name)

            if valid_base_name != base_name:
                invalid_files.append(file_name)
                valid_files.append(valid_base_name.join(file_name.rsplit(base_name, 1)))

        if invalid_files:
            self.files_name_for_error_message = [invalid_files, valid_files]
            return True

        return False

    def remove_separators_from_name(self, base_name) -> str:
        """
        Removes separators from a given name of folder or file.

        Args:
            base_name: The base name of the folder/file.

        Return:
            The base name without separators.
        """

        for separator in ENTITY_NAME_SEPARATORS:
            if separator in base_name:
                base_name = base_name.replace(separator, "")

        return base_name
