from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON
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
    conf_data = ConfJSON.from_path(CONTENT_PATH / "Tests/conf.json")
    skipped_tests_keys = list(conf_data.skipped_tests.keys())

    def is_valid_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            if self.graph.find_test_playbook_without_uses(
                content_item.object_id, self.skipped_tests_keys
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(content_item.name),
                        content_object=content_item,
                    )
                )

        return validation_results
