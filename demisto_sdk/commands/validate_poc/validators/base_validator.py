from abc import ABC, abstractmethod

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ValidationResult(BaseModel):
    error_code: str
    is_valid: bool
    message: str

class BaseValidator(ABC, BaseModel):
    error_code: str
    description: str
    content_item: BaseContent
    is_auto_fixable: bool
    related_field: str
    
    @abstractmethod
    @classmethod
    def should_run(cls, content_item: BaseContent) -> bool:
        return True
    @abstractmethod
    @classmethod
    def is_valid(cls, content_item: BaseContent) -> ValidationResult:
        pass
    @abstractmethod
    @classmethod
    def fix(cls, content_item: BaseContent) -> None:
        pass
