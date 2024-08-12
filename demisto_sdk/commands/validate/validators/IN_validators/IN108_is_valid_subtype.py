from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import PYTHON_SUBTYPES
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class ValidSubtypeValidator(BaseValidator[ContentTypes]):
    error_code = "IN108"
    description = "Validate wether the subtype is valid or not."
    rationale = "This field describes the major python version, `python2` or `python3`."
    error_message = "The subtype {0} is invalid, please change to python2 or python3."
    fix_message = ""
    related_field = "subtype"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.subtype),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.type == "python"
            and content_item.subtype not in PYTHON_SUBTYPES
        ]
