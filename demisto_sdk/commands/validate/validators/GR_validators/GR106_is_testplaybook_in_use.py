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
        "Checks that every test playbook is linked to at least one content item."
        " (the content item has a 'tests:' key with the id of the test playbook)"
    )
    rationale = (
        "In the demisto/content repo, unlinked test playbooks are not run in PRs unless the test playbook itself is modified. Proper linkage of test playbooks ensures content quality. "
        "See  https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-the-playbook-to-your-project"
    )
    error_message = "Test playbook '{}' is not linked to any content item. Make sure at least one integration, script or playbook mention it under the `tests:` key."
    related_field = "tests"
    is_auto_fixable = False
    conf_data = ConfJSON.from_path(CONTENT_PATH / "Tests/conf.json")
    skipped_tests_keys = list(conf_data.skipped_tests.keys())

    def is_valid_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        
        test_playbook_ids_to_validate = (
            [item.object_id for item in content_items] if not validate_all_files else []
        )
        invalid_content_items = self.graph.find_unused_test_playbook(
                test_playbook_ids_to_validate, self.skipped_tests_keys
            )
        validation_results = []
        for content_item in invalid_content_items:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(content_item.object_id),
                        content_object=content_item,
                    )
                )

        return validation_results
