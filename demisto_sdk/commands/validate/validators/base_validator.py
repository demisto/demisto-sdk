from abc import ABC
from pathlib import Path
from typing import ClassVar, Generic, List, Optional, Tuple, Type, TypeVar

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
            "file path": str(self.file_path),
            "is_valid": self.is_valid,
            "error code": self.error_code,
            "message": self.message,
        }


class FixingResult(BaseModel):
    error_code: str
    message: str
    file_path: Path

    @property
    def format_readable_message(self):
        return f"Fixing {str(self.file_path)}: {self.error_code} - {self.message}"

    @property
    def format_json_message(self):
        return {
            "file path": str(self.file_path),
            "error code": self.error_code,
            "message": self.message,
        }


ContentTypes = TypeVar("ContentTypes", bound=BaseContent)


class BaseValidator(ABC, BaseModel, Generic[ContentTypes]):
    content_types: TypeVar
    error_code: ClassVar[str]
    description: ClassVar[str]
    error_message: ClassVar[str]
    fixing_message: ClassVar[Optional[str]] = None
    is_auto_fixable: ClassVar[bool]
    related_field: ClassVar[str]
    expected_git_statuses: ClassVar[Optional[List[str]]] = None

    def get_content_types(self) -> Tuple[Type[BaseContent]]:
        return self.content_types.__constraints__ or (self.content_types.__bound__,)

    def should_run(
        self,
        content_item: ContentTypes,
        ignorable_errors: list,
        support_level_dict: dict,
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
                isinstance(content_item, self.get_content_types()),
                should_run_according_to_status(
                    content_item.git_status, self.expected_git_statuses
                ),
                not is_error_ignored(
                    self.error_code, content_item.ignored_errors, ignorable_errors
                ),
                not is_support_level_support_validation(
                    self.error_code, support_level_dict, content_item.support
                ),
            ]
        )

    def is_valid(self, content_item: ContentTypes, **kwargs) -> ValidationResult:
        raise NotImplementedError

    def fix(self, content_item: ContentTypes, **kwargs) -> FixingResult:
        raise NotImplementedError

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )


def is_error_ignored(
    err_code: str, ignored_errors: List[str], ignorable_errors: List[str]
) -> bool:
    """
    Check if the given validation error code is ignored by the current item ignored error list.

    Args:
        err_code (str): The validation's error code.
        ignored_errors (list): The list of the content item ignored errors.
        ignorable_errors (list): The list of the ignorable errors.

    Returns:
        bool: True if the given error code should and allow to be ignored by the given item. Otherwise, return False.
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


def should_run_according_to_status(
    content_item_git_status: Optional[str], expected_git_statuses: Optional[List[str]]
) -> bool:
    """
    Check if the given content item git status is in the given expected git statuses for the specific validation.

    Args:
        content_item_git_status (Optional[str]): The content item git status (Added, Modified, Renamed, Deleted or None if file was created via -i/-a)
        expected_git_statuses (Optional[List[str]]): The validation's expected git statuses, if None then validation should run on all cases.

    Returns:
        bool: True if the given validation should run on the content item according to the expected git statuses. Otherwise, return False.
    """
    return not expected_git_statuses or content_item_git_status in expected_git_statuses
