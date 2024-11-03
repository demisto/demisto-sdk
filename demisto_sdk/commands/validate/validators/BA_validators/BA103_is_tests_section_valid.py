
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsTestsSectionValidValidator(BaseValidator[ContentTypes]):
    error_code = "BA103"
    description = "Validate that the test section is either stating explicitly "no tests" or has a non-empty list of tests."
    rationale = "Enforce a generic standard for making sure ther're tests."
    error_message = "The following {0} tests section is malformed. It should either be a non empty list for tests or "No tests" in case there're no tests."
    related_field = "tests"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED, GitStatuses.RENAMED]

    
    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        

    
