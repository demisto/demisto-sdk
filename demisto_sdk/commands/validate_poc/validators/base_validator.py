from abc import ABC
from typing import Tuple, Type

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ValidationResult(BaseModel):
    error_code: str
    message: str
    file_path: str
    is_valid: bool
    
    @property
    def format_message(self):
        return f"{self.file_path}: {self.error_code} - {self.message}"


class BaseValidator(ABC, BaseModel):
    error_code: str
    description: str
    is_auto_fixable: bool
    related_field: str
    content_types: Tuple[Type[BaseContent], ...]

    @classmethod
    def should_run(cls, content_item: BaseContent) -> bool:
        return isinstance(content_item, cls.content_types) and cls.error_code not in content_item.ignored_errors

    @classmethod
    def is_valid(cls, content_item: BaseContent) -> ValidationResult:
        raise NotImplementedError

    @classmethod
    def fix(cls, content_item: BaseContent) -> None:
        raise NotImplementedError
