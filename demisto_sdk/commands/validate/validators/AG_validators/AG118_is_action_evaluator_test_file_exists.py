from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction

EVALUATOR_TEST_FILE_SUFFIX = "_test.yml"


class IsActionEvaluatorTestFileExistsValidator(BaseValidator[ContentTypes]):
    error_code = "AG118"
    description = "Checks that the AgentixAction has an evaluator test file ('<ActionName>_test.yml' next to '<ActionName>.yml')."
    error_message = (
        "The AgentixAction '{0}' is missing its evaluator test file. "
        "Please create a file named '{1}' in the action's directory."
    )
    related_field = "test"
    rationale = (
        "An AgentixAction must be accompanied by an evaluator test file named "
        "'<ActionName>_test.yml' in the same directory under 'AgentixActions/'. "
        "The evaluator test file defines the scenarios used to evaluate the "
        "action's behavior, so it is required for the action to be valid."
    )
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            expected_test_file_name = (
                f"{content_item.path.parent.name}{EVALUATOR_TEST_FILE_SUFFIX}"
            )
            test_file_path = content_item.path.with_name(expected_test_file_name)
            exists = self.case_sensitive_exists(test_file_path)
            if not exists:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name,
                            expected_test_file_name,
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def case_sensitive_exists(self, test_file_path: Path) -> bool:
        """Checks if the evaluator test file's path (case sensitive) exists.

        Args:
            test_file_path (Path): The evaluator test file's path to check.

        Returns:
            bool: If the path exists, taking into consideration case sensitivity.
        """
        if not test_file_path.exists():
            return False
        # Checking if the file exists is not enough since Path.exists() isn't
        # always case sensitive (related to file system configuration).
        actual_files = [file.name for file in test_file_path.parent.iterdir()]
        return test_file_path.name in actual_files
