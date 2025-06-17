from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookTestUseCaseDependenciesValidator(BaseValidator[ContentTypes]):
    error_code = "PB134"
    description = "Validate test use case dependencies in the file docstring"
    rationale = "Avoid failures in finding and installing dependencies"
    error_message = "Invalid dependencies in {test_use_case_name}. {reason}."
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.TEST_CODE_FILE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Obtains playbooks where tests referenced in the YML do not exist in the appropriate
        directory in the pack.

        Args:
            content_items (Iterable[ContentTypes]): Playbooks to be validated.

        Returns:
            List[ValidationResult]: List of ValidationResult objects for any referenced tests
                                    that do not exist in the pack.
        """
        validation_results: List[ValidationResult] = []

        for content_item in content_items:
            for test_use_case_name in content_item.test_use_case_names:
                test_use_case_path = (
                    content_item.pack.path / "TestUseCases" / f"{test_use_case_name}.py"
                )
                if test_use_case_path.exists():
                    # Work in progress
                    pass

        return validation_results
