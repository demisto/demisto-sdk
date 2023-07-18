from abc import ABC
from pathlib import Path
from typing import ClassVar, Tuple, Type

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ValidationResult(BaseModel):
    error_code: str
    message: str
    file_path: Path
    is_valid: bool
    
    @property
    def format_message(self):
        return f"{str(self.file_path)}: {self.error_code} - {self.message}"


class BaseValidator(ABC, BaseModel):
    error_code: ClassVar[str]
    description: ClassVar[str]
    error_message: ClassVar[str]
    is_auto_fixable: ClassVar[bool]
    related_field: ClassVar[str]
    content_types: ClassVar[Tuple[Type[BaseContent], ...]]

    @classmethod
    def should_run(cls, content_item: BaseContent) -> bool:
        return isinstance(content_item, cls.content_types) and cls.error_code not in content_item.ignored_errors

    @classmethod
    def is_valid(cls, content_item: BaseContent) -> ValidationResult:
        raise NotImplementedError

    @classmethod
    def fix(cls, content_item: BaseContent) -> None:
        raise NotImplementedError
