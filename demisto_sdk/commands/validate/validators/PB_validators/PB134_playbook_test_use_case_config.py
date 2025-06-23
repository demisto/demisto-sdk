from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import (
    RelatedFileType,
    TestUseCaseRelatedFile,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class PlaybookTestUseCaseConfigValidator(BaseValidator[ContentTypes]):
    error_code = "PB134"
    description = "Validate test use case configuration in the file docstring"
    rationale = "Avoid failures in finding and installing dependencies"
    error_message = "Invalid configuration in test use case: {path}. {reason}."
    related_field = "tests"
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
            # Optional since "TestUseCases" folder may not exist in the environment
            test_use_cases_dir = content_item.path / "TestUseCases"
            if not test_use_cases_dir.exists():
                logger.debug(f"Pack '{content_item.name}' has no test use cases.")
                continue

            for test_use_case in content_item.test_use_cases:
                is_valid, reason = self.validate_config_docstring(test_use_case)
                if not is_valid:
                    path = test_use_case.file_path.relative_to(content_item.path)
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(path=path, reason=reason),
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
        try:
            config = test_use_case.config_docstring

        except SyntaxError:
            return False, "Invalid Python syntax"

        except JSONDecodeError:
            return False, "Invalid JSON object"

        additional_needed_packs = config.get("additional_needed_packs", {})
        if not isinstance(additional_needed_packs, dict):
            return False, "Invalid object schema"

        return True, ""
