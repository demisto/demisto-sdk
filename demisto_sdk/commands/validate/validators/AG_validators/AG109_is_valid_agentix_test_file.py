from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import yaml

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.strict_objects.agentix_test import AgentixTestFile
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsValidAgentixTestFileValidator(BaseValidator[ContentTypes]):
    error_code = "AG109"
    description = "Validates Agentix test YAML files in test_data directory."
    rationale = "Ensures Agentix test cases are correctly structured and follow formatting rules for reliable evaluation."
    error_message = "Errors found in Agentix test file '{0}':\n{1}"
    related_field = "test_data"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            test_data_dir = content_item.path.parent / "test_data"
            if not test_data_dir.exists() or not test_data_dir.is_dir():
                continue

            for test_file_path in test_data_dir.glob("*.yaml"):
                errors = self.validate_test_file(test_file_path)
                if errors:
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                test_file_path.name, "\n".join(errors)
                            ),
                            content_object=content_item,
                            path=test_file_path,
                        )
                    )
        return validation_results

    def validate_test_file(self, file_path: Path) -> List[str]:
        errors = []
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return [f"Invalid YAML syntax: {str(e)}"]
        except Exception as e:
            return [f"Failed to read file: {str(e)}"]

        if not isinstance(data, dict) or "tests" not in data:
            return ["Root structure must be a dictionary containing a 'tests' key."]

        if not isinstance(data["tests"], list):
            return ["The 'tests' key must be a list of test cases."]

        try:
            AgentixTestFile(**data)
        except Exception as exc:
            # Pydantic validation will catch missing fields, type mismatches,
            # and the prompt period requirement.
            # We simplify the error message for the user.
            errors_func = getattr(exc, "errors", None)
            if callable(errors_func):
                for error in errors_func():
                    loc = " -> ".join(str(x) for x in error.get("loc", []))
                    msg = error.get("msg")
                    errors.append(f"[{loc}]: {msg}")
            else:
                errors.append(str(exc))

        # Additional logic for evaluation modes
        for i, test in enumerate(data.get("tests", [])):
            if not isinstance(test, dict):
                continue

            # Check for evaluation modes consistency
            modes = {"any_of", "sequence", "expected_outcomes"}
            present_modes = modes.intersection(test.keys())
            if len(present_modes) > 1:
                errors.append(
                    f"Test case {i} ('{test.get('name', 'Unnamed')}') has multiple evaluation modes: {', '.join(present_modes)}. Only one is allowed."
                )

            # Check for expected_error vs actions
            outcomes_list = [
                test.get("expected_outcomes"),
                test.get("any_of"),
                test.get("sequence"),
            ]
            for outcomes in outcomes_list:
                if not isinstance(outcomes, list):
                    continue
                for j, outcome in enumerate(outcomes):
                    if not isinstance(outcome, dict):
                        continue
                    if "expected_error" in outcome and (
                        "action" in outcome or "actions" in outcome
                    ):
                        errors.append(
                            f"Test case {i}, outcome {j}: 'expected_error' cannot be used with 'action' or 'actions'."
                        )

        return errors
