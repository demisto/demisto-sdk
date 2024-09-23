
from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsInvalidPacksDependenciesValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR999"
    description = ""
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False


    def obtain_invalid_content_items_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        v = []
        for content_item in content_items:
            if pack_dependencies := content_item.pack_metadata_dict.get("dependencies", {}): # type: ignore
                ...
            v.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message,
                    content_object=content_item,
                ))


        return v
