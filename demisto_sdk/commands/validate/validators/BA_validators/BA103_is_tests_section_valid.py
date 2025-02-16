from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsTestsSectionValidValidator(BaseValidator[ContentTypes]):
    error_code = "BA103"
    description = 'Validate that the test section is either stating explicitly "No tests" or has a non-empty list of tests.'
    rationale = "Enforce a generic standard for making sure there are tests."
    error_message = 'The tests section of the following {0} is malformed. It should either be a non empty list for tests or "No tests" in case there are no tests.'
    related_field = "tests"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.content_type),
                content_object=content_item,
            )
            for content_item in content_items
            if isinstance(content_item.tests, str)
            and content_item.tests not in ("No tests (auto formatted)", "No tests")
            or isinstance(content_item.tests, list)
            and len(content_item.tests) == 0
        ]
