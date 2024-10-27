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
        " (the content item has a 'tests:' key with the ID of the test playbook)"
    )
    rationale = (
        "In the demisto/content repo, unlinked test playbooks are not run in CI (for PRs) unless the test playbook itself is modified. Proper linkage of test playbooks ensures content quality. "
        "See  https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-the-playbook-to-your-project"
    )
    error_message = "Test playbook '{}' is not linked to any content item. Make sure at least one integration, script or playbook mentions the test-playbook ID under the `tests:` key."
    related_field = "tests"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        conf_data = ConfJSON.from_path(CONTENT_PATH / "Tests/conf.json")
        test_playbooks_ids_to_skip = list(
            set(conf_data.skipped_tests.keys()) | set(conf_data.reputation_tests)
        )
        #  the collect test for reputation playbooks checks the reputation_tests field in conf.json and not the `tests` key in the yml
        test_playbook_ids_to_validate = (
            [] if validate_all_files else [item.object_id for item in content_items]
        )
        invalid_content_items = self.graph.find_unused_test_playbook(
            test_playbook_ids_to_validate, test_playbooks_ids_to_skip
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.object_id),
                content_object=content_item,
            )
            for content_item in invalid_content_items
        ]
