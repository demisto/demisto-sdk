from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    GitStatuses,
)
from demisto_sdk.commands.common.tools import get_files_in_dir
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]
ENTITY_NAME_SEPARATORS = ["_", "-"]


class FileNameHasSeparatorsValidator(BaseValidator[ContentTypes]):
    error_code = "BA109"
    description = (
        "Check if there are separators in the script or integration files names."
    )
    rationale = "Filenames for scripts and integrations should not contain separators to maintain consistency and readability."
    error_message = "The {item_type} files should be named without any separators in the base name:\n{params}"
    related_field = "file path"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.ADDED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    item_type=content_item.content_type,
                    params="\n".join(
                        [
                            f"'{file_name[0]}' should be named '{file_name[1]}'"
                            for file_name in invalid_files
                        ]
                    ),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if bool(invalid_files := self.check_separators_in_files(content_item))
        ]

    def check_separators_in_files(self, content_item: ContentTypes) -> list[tuple]:
        """
        Check if there are separators in the file names of the content item.

        Args:
            content_item: The content item to check.

        Returns:
            bool: True if there are invalid file names, False otherwise.
        """
        invalid_files: List[tuple] = []

        files_to_check = get_files_in_dir(
            str(content_item.path.parent), ["yml", "py", "md", "png"], False
        )

        files_to_check = sorted(
            files_to_check
        )  # Used to keep the error message consistent

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
                invalid_files.append(
                    (file_name, valid_base_name.join(file_name.rsplit(base_name, 1)))
                )

        if invalid_files:
            return invalid_files

        return []

    def remove_separators_from_name(self, base_name: str) -> str:
        """
        Remove separators from a given name.

        Args:
            base_name (str): The base name to remove separators from.

        Returns:
            str: The base name without separators.
        """
        for separator in ENTITY_NAME_SEPARATORS:
            if separator in base_name:
                base_name = base_name.replace(separator, "")

        return base_name
