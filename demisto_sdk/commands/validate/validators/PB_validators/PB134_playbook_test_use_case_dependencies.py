from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import (
    RelatedFileType,
    TestUseCaseRelatedFile,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookTestUseCaseConfigValidator(BaseValidator[ContentTypes]):
    error_code = "PB134"
    description = "Validate test use case configuration in the file docstring"
    rationale = "Avoid failures in finding and installing dependencies"
    error_message = "Invalid configuration in {test_use_case_name}. {reason}."
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
            if not content_item.in_pack:
                logger.debug(f"Playbook: {content_item.object_id} not in pack.")
                continue

            pack: Pack = content_item.pack

            # Optional since "TestUseCases" folder may not exist in the environment
            test_use_cases_dir = pack.path / "TestUseCases"
            if not test_use_cases_dir.exists():
                continue

            for test_use_case in pack.test_use_cases:
                is_valid, reason = self.validate_config_docstring(test_use_case)
                if not is_valid:
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                test_use_case_name=test_use_case.name,
                                reason=reason,
                            ),
                            content_object=content_item,
                        )
                    )

        return validation_results

    @staticmethod
    def validate_config_docstring(
        test_use_case: TestUseCaseRelatedFile,
    ) -> Tuple[bool, str]:
        try:
            config = test_use_case.config_docstring
            is_valid, reason = True, ""

        except SyntaxError:
            is_valid, reason = False, "Invalid Python syntax"

        except JSONDecodeError:
            is_valid, reason = False, "Invalid JSON object"

        additional_needed_packs = config.get("additional_needed_packs", {})
        if not isinstance(additional_needed_packs, dict):
            is_valid, reason = False, "Invalid config schema"

        file_path = test_use_case.file_path
        if not is_valid:
            logger.debug(f"Invalid test use case config in {file_path}. {reason}.")

        return is_valid, reason
