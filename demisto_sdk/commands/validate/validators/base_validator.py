from abc import ABC
from pathlib import Path
from typing import ClassVar, List, Tuple, Type

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ValidationResult(BaseModel):
    error_code: str
    message: str
    file_path: Path
    is_valid: bool

    @property
    def format_readable_message(self):
        return f"{str(self.file_path)}: {self.error_code} - {self.message}"

    @property
    def format_json_message(self):
        return {
            "file path": self.file_path,
            "is_valid": self.is_valid,
            "error code": self.error_code,
            "message": self.message,
        }


class BaseValidator(ABC, BaseModel):
    error_code: ClassVar[str]
    description: ClassVar[str]
    error_message: ClassVar[str]
    is_auto_fixable: ClassVar[bool]
    related_field: ClassVar[str]
    content_types: ClassVar[Tuple[Type[BaseContent], ...]]

    @classmethod
    def should_run(
        cls, content_item: BaseContent, ignorable_errors: list, support_level_dict: dict
    ) -> bool:
        """check wether to run validation on the given content item or not.

        Args:
            content_item (BaseContent): The content item to run the validation on.
            ignorable_errors (list): The list of the errors that can be ignored.
            support_level_dict (dict): A dict with the lists of validation to run / not run according to the support level.

        Returns:
            bool: True if the validation should run. Otherwise, return False.
        """
        return all(
            [
                isinstance(content_item, cls.content_types),
                not is_error_ignored(
                    cls.error_code, content_item.ignored_errors, ignorable_errors
                ),
                not is_support_level_support_validation(
                    cls.error_code, support_level_dict, content_item.support
                ),
            ]
        )

    @classmethod
    def is_valid(cls, content_item: BaseContent) -> ValidationResult:
        raise NotImplementedError

    @classmethod
    def fix(cls, content_item: BaseContent) -> None:
        raise NotImplementedError


def is_error_ignored(err_code: str, ignored_errors: List[str], ignorable_errors: List[str]) -> bool:
    """
    Check if the given validation error code is ignored by the current item ignored error list.

    Args:
        err_code (str): The validation's error code.
        ignored_errors (list): The list of the content item ignored errors.
        ignorable_errors (list): The list of the ignorable errors.

    Returns:
        bool: True if the given error code should and allow to be ignored by the given item, otherwise return False.
    """
    return err_code in ignored_errors and err_code in ignorable_errors


def is_support_level_support_validation(
    err_code: str, support_level_dict: dict, item_support_level: str
) -> bool:
    """
    Check if the given validation error code is ignored according to the item's support level.

    Args:
        err_code (str): The validation's error code.
        support_level_dict (dict): The support level dictionary from the config file.
        item_support_level (str): The content item support level.

    Returns:
        bool: True if the given error code is in the ignored section of the support level dict corresponding to the item's support level, otherwise return False.
    """
    return err_code in support_level_dict.get(item_support_level, {}).get("ignore", [])
