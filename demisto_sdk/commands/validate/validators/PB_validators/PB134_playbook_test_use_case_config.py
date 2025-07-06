from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.tools import get_all_repo_pack_ids
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import (
    RelatedFileType,
    TestUseCaseRelatedFile,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ALL_PACK_IDS = get_all_repo_pack_ids()

ContentTypes = Playbook


class PlaybookTestUseCaseConfigValidator(BaseValidator[ContentTypes]):
    error_code = "PB134"
    description = "Validate test use case configuration in the file docstring"
    rationale = "Avoid failures in finding and installing dependencies"
    error_message = "Invalid configuration in test use case: {name}. {reason}."
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.TEST_CODE_FILE]
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

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
            for test_use_case in content_item.test_use_cases:
                is_valid, reason = self.validate_config_docstring(test_use_case)
                if not is_valid:
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                name=test_use_case.name, reason=reason
                            ),
                            content_object=content_item,
                        )
                    )

        return validation_results

    @staticmethod
    def validate_config_docstring(
        test_use_case: TestUseCaseRelatedFile,
    ) -> Tuple[bool, str]:
        """Validates the test use case docstring in the Python file.

        Args:
            test_use_case (TestUseCaseRelatedFile): A related pack test use case.

        Returns:
            Tuple[bool, str]: A tuple of a boolean indicating whether the configuration
            docstring is valid or not and the error, if any.
        """
        # Step 1: Check Python syntax and JSON object
        try:
            config = test_use_case.config_docstring

        except SyntaxError:
            return False, "Invalid Python syntax"

        except JSONDecodeError:
            return False, "Invalid JSON object"

        # Step 2: Check schema fields
        additional_needed_packs = config.get("additional_needed_packs", {})
        if not isinstance(additional_needed_packs, dict):
            return False, "Invalid object schema"

        # Step 3: Check pack IDs
        invalid_pack_ids = {
            pack_id
            for pack_id in additional_needed_packs.keys()
            if pack_id not in ALL_PACK_IDS
        }
        if invalid_pack_ids:
            return False, f"Unknown packs: {', '.join(invalid_pack_ids)}"

        # If all passes, return True
        return True, ""
