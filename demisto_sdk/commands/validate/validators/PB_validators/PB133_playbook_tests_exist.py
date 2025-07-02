from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

TEST_USE_CASE_SUFFIX = "_use_case_test"
TESTS_LIST_ITEMS_TO_SKIP = ("no test", "run all tests")

ContentTypes = Playbook


class PlaybookTestsExistValidator(BaseValidator[ContentTypes], ABC):
    error_code = "PB133"
    description = "Validate playbook tests"
    rationale = "Avoid testing failures from referenced tests that do not exist"
    error_message = "Playbook '{name}' references the following missing {test_type}s: {missing_tests}."
    related_field = "tests"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []

        file_paths_to_validate = (
            [
                str(content_item.path.relative_to(CONTENT_PATH))
                for content_item in content_items
            ]
            if not validate_all_files
            else []
        )
        # Query graph for playbooks that have "TESTED BY" relationship objects that are *not* in content repository
        content_items_with_unknown_tests = self.graph.get_unknown_playbook_tests(
            file_paths_to_validate
        )

        for content_item in content_items_with_unknown_tests:
            missing_test_playbooks_ids = set()
            missing_test_use_case_names = set()

            for playbook_test in content_item.tested_by:
                test_id = playbook_test.object_id

                if test_id.casefold().startswith(TESTS_LIST_ITEMS_TO_SKIP):
                    continue

                if TEST_USE_CASE_SUFFIX not in test_id:
                    playbook_id = test_id
                    missing_test_playbooks_ids.add(playbook_id)

                elif content_item.pack_path:
                    pack_test_use_cases_path = content_item.pack_path / "TestUseCases"
                    test_name = f"{test_id}.py"
                    test_use_case_path = pack_test_use_cases_path / test_name

                    if (
                        pack_test_use_cases_path.exists()
                        and not test_use_case_path.exists()
                    ):
                        missing_test_use_case_names.add(test_name)

            if missing_test_playbooks_ids:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            name=content_item.name,
                            test_type="test playbook",
                            missing_tests=", ".join(missing_test_playbooks_ids),
                        ),
                        content_object=content_item,
                    )
                )

            if missing_test_use_case_names:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            name=content_item.name,
                            test_type="test use case",
                            missing_tests=", ".join(missing_test_use_case_names),
                        ),
                        content_object=content_item,
                    )
                )

        return validation_results
