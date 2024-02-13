from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import (
    ClassVar,
    Generic,
    Iterable,
    List,
    Optional,
    TypeVar,
    get_args,
)

from pydantic import BaseModel

from demisto_sdk.commands.common.constants import GitStatuses, RelatedFileType
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
    BaseContentMetaclass,
)

ContentTypes = TypeVar("ContentTypes", bound=BaseContent)


class BaseValidator(ABC, BaseModel, Generic[ContentTypes]):
    """The generic validator class to inherit from.
    Class variables:
    error_code: (ClassVar[str]): The validation's error code.
    description: (ClassVar[str]): The validation's error description.
    error_message: (ClassVar[str]): The validation's error message.
    fix_message: (ClassVar[str]): The validation's fixing message.
    related_field: (ClassVar[str]): The validation's related field.
    expected_git_statuses: (ClassVar[Optional[List[GitStatuses]]]): The list of git statuses the validation should run on.
    expected_file_types: (ClassVar[Optional[List[RelatedFileType]]]): The list of file types (suffixes) the validation should run on.
    run_on_deprecated: (ClassVar[bool]): Wether the validation should run on deprecated items or not.
    is_auto_fixable: (ClassVar[bool]): Whether the validation has a fix or not.
    graph_interface: (ClassVar[ContentGraphInterface]): The graph interface.
    dockerhub_api_client (ClassVar[DockerHubClient): the docker hub api client.
    """

    error_code: ClassVar[str]
    description: ClassVar[str]
    error_message: ClassVar[str]
    fix_message: ClassVar[str] = ""
    related_field: ClassVar[str]
    expected_git_statuses: ClassVar[Optional[List[GitStatuses]]] = []
    expected_file_types: ClassVar[List[RelatedFileType]] = [
        RelatedFileType.YML,
        RelatedFileType.JSON,
    ]
    run_on_deprecated: ClassVar[bool] = False
    is_auto_fixable: ClassVar[bool] = False
    graph_interface: ClassVar[ContentGraphInterface] = None

    def get_content_types(self):
        args = (get_args(self.__orig_bases__[0]) or get_args(self.__orig_bases__[1]))[0]  # type: ignore
        if isinstance(args, (BaseContent, BaseContentMetaclass)):
            return args
        return get_args(args)

    def should_run(
        self,
        content_item: ContentTypes,
        ignorable_errors: list,
        support_level_dict: dict,
    ) -> bool:
        """check whether to run validation on the given content item or not.

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
                should_run_on_deprecated(self.run_on_deprecated, content_item),
                should_run_according_to_file_type_and_status(
                    content_item, self.expected_file_types, self.expected_git_statuses
                ),
                not is_error_ignored(
                    self.error_code, content_item.ignored_errors, ignorable_errors
                ),
                not is_support_level_support_validation(
                    self.error_code, support_level_dict, content_item.support_level
                ),
            ]
        )

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        raise NotImplementedError

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        raise NotImplementedError

    @property
    def graph(self) -> ContentGraphInterface:
        if not self.graph_interface:
            logger.info("Graph validations were selected, will init graph")
            BaseValidator.graph_interface = ContentGraphInterface()
            update_content_graph(
                BaseValidator.graph_interface,
                use_git=True,
            )
        return self.graph_interface

    def __dir__(self):
        # Exclude specific properties from being displayed when hovering over 'self'
        return [attr for attr in dir(type(self)) if attr != "graph"]

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )
        # Exclude the properties from the repr
        fields = {"graph": {"exclude": True}, "dockerhub_client": {"exclude": True}}


class BaseResult(BaseModel):
    validator: BaseValidator
    message: str
    content_object: BaseContent

    @property
    def format_readable_message(self):
        return f"{str(self.content_object.path.relative_to(CONTENT_PATH))}: [{self.validator.error_code}] - {self.message}"

    @property
    def format_json_message(self):
        return {
            "file path": str(self.content_object.path.relative_to(CONTENT_PATH)),
            "error code": self.validator.error_code,
            "message": self.message,
        }


class ValidationResult(BaseResult, BaseModel):
    """This is a class for validation results."""


class FixResult(BaseResult, BaseModel):
    """This is a class for fix results."""


class NonContentItemResult(BaseResult, BaseModel):
    validator: Optional[BaseValidator] = None  # type: ignore[assignment]
    message: str
    content_object: Optional[BaseContent] = None  # type: ignore[assignment]
    error_code: str
    path: Path

    @property
    def format_readable_message(self):
        return f"{str(self.path.relative_to(CONTENT_PATH))}: [{self.error_code}] - {self.message}"

    @property
    def format_json_message(self):
        return {
            "file path": str(self.path.relative_to(CONTENT_PATH)),
            "error code": self.error_code,
            "message": self.message,
        }


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


def should_run_on_deprecated(run_on_deprecated, content_item):
    if content_item.deprecated and not run_on_deprecated:
        return False
    return True


def should_run_according_to_file_type_and_status(
    content_item: ContentTypes,
    expected_file_types: List[RelatedFileType],
    expected_git_statuses: Optional[List[GitStatuses]],
) -> bool:
    """
    Check if the given content item is matching the validation's requirement by file type and git status.

    Args:
        content_item (ContentTypes): The content item to decide whether to run the validation on or not.
        expected_file_types (List[RelatedFileType]): The validation's expected file types.
        expected_git_statuses (Optional[List[str]]): The validation's expected git statuses, if None then validation should run on all cases.

    Returns:
        bool: True if the given validation should run on the content item according to the expected git statuses and file_types. Otherwise, return False.
    """
    if content_item.file_type in expected_file_types:
        return (
            not expected_git_statuses
            or content_item.git_status in expected_git_statuses
        )
    elif related_content_types := [
        related_content_type
        for related_content_type in expected_file_types
        if related_content_type in content_item.related_content
    ]:
        return not expected_git_statuses or any(
            content_item.related_content[related_content_type]["git_status"]
            == expected_git_statuses
            for related_content_type in related_content_types
        )
    return False
