from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = TestPlaybook


class IsTestPlaybookInUseValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR106"
    description = (
        "Ensure that each test playbook is linked to at least one content item."
    )
    rationale = (
        "Proper linkage of test playbooks ensures comprehensive testing. For guidelines,"
        " visit: https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-the-playbook-to-your-project"
    )
    error_message = "Test playbook '{}' is not linked to any content item. Please ensure it is properly utilized."
    related_field = "tests"
    is_auto_fixable = False

    def is_valid_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_error = []
        for content_item in content_items:
            if self.graph.find_test_playbook_without_uses(content_item.name):
                validation_error.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(content_item.name),
                        content_object=content_item,
                    )
                )
        return validation_error
