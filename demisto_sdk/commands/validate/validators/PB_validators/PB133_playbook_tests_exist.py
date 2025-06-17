from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Literal, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookTestsExistValidator(BaseValidator[ContentTypes]):
    error_code = "PB133"
    description = "Validate playbook tests"
    rationale = "Avoid testing failures from referenced tests that do not exist"
    error_message = "Test '{test_name}' is referenced in playbook '{id}' but is missing from the '{test_dir_name}' directory."
    related_field = ""
    is_auto_fixable = False

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

            pack_name = content_item.pack_name
            test_playbooks_dir = content_item.pack.path / "TestPlaybooks"
            test_use_cases_dir = content_item.pack.path / "TestUseCases"

            logger.debug(f"Validating against test playbooks under {pack_name}.")
            validation_results += self._validate_test_references(
                content_item=content_item,
                test_dir_name="TestPlaybooks",
                referenced_tests=content_item.test_playbook_ids,
                existing_tests=self._get_test_playbook_ids(test_playbooks_dir),
            )

            if test_use_cases_dir.exists():
                # Optional since "TestUseCases" folder may not exist in the environment
                logger.debug(f"Validating against test use cases under {pack_name}.")
                validation_results += self._validate_test_references(
                    content_item=content_item,
                    test_dir_name="TestUseCases",
                    referenced_tests=content_item.test_use_case_names,
                    existing_tests=self._get_test_use_case_names(test_use_cases_dir),
                )

        return validation_results

    def _validate_test_references(
        self,
        content_item: ContentTypes,
        test_dir_name: Literal["TestPlaybooks", "TestUseCases"],
        referenced_tests: Set[str],
        existing_tests: Set[str],
    ) -> List[ValidationResult]:
        """
        Validates referenced tests against existing tests in the pack (e.g., test playbooks or test use cases)

        Args:
            content_item (ContentTypes): The Playbook being validated.
            test_dir_name (Literal): The name of the directory where the tests are expected to be found.
            referenced_tests (Set[str]): A set of test names or IDs referenced in the content item's YML.
            existing_tests (Set[str]): A set of test names or IDs found in the specified test directory.

        Returns:
            List[ValidationResult]: List of ValidationResult objects for any referenced tests
                                    that do not exist in the `existing_tests` set.
        """
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    id=content_item.object_id,
                    test_name=referenced_test,
                    test_dir_name=test_dir_name,
                ),
                content_object=content_item,
            )
            for referenced_test in referenced_tests
            if referenced_test not in existing_tests
        ]

    @staticmethod
    def _get_test_playbook_ids(pack_test_playbooks_dir: Path) -> Set[str]:
        """Retrieves the IDs of all test playbooks in the pack "TestPlaybooks" directory.

        Args:
            pack_test_playbooks_dir (Path): The path to the directory containing test playbooks.

        Returns:
            Set[str]: A set of unique playbook IDs found in the directory, if exists.
        """
        if not pack_test_playbooks_dir.exists():
            return set()

        pack_test_playbook_ids = set()
        for test_playbook_path in pack_test_playbooks_dir.iterdir():
            parser = PlaybookParser(
                test_playbook_path,
                list(MarketplaceVersions),
                pack_supported_modules=[],
            )
            if parser.object_id:
                pack_test_playbook_ids.add(parser.object_id)
        return pack_test_playbook_ids

    @staticmethod
    def _get_test_use_case_names(pack_test_use_case_dir: Path) -> Set[str]:
        """Retrieves the file names (without the ".py" extension) in the pack "TestUseCases" directory.

        Args:
            pack_test_use_case_dir (Path): The path to the directory containing test use cases.

        Returns:
            Set[str]: A set of unique test use case names if the directory, if exists.
        """
        if not pack_test_use_case_dir.exists():
            return set()

        return {
            # Remove .py file extension
            str(path.relative_to(pack_test_use_case_dir).with_suffix(""))
            for path in pack_test_use_case_dir.rglob("*")  # recursive search
            if path.is_file()
        }
