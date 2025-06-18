from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
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
    related_file_type = [RelatedFileType.YML, RelatedFileType.TEST_CODE_FILE]

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

            logger.debug(f"Validating against test playbooks under {pack.name}.")
            pack_test_playbook_ids = {
                test_playbook.id for test_playbook in pack.test_playbooks
            }
            validation_results.extend(
                [
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            id=content_item.object_id,
                            test_name=test_playbook_id,
                            test_dir_name="TestPlaybooks",
                        ),
                        content_object=content_item,
                    )
                    for test_playbook_id in content_item.test_playbook_ids
                    if test_playbook_id not in pack_test_playbook_ids
                ]
            )

            test_use_cases_dir = pack.path / "TestUseCases"
            if test_use_cases_dir.exists():
                # Optional since "TestUseCases" folder may not exist in the environment
                logger.debug(f"Validating against test use cases under {pack.name}.")
                pack_test_use_case_names = {
                    test_use_case.name for test_use_case in pack.test_use_cases
                }
                validation_results.extend(
                    [
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                id=content_item.object_id,
                                test_name=test_use_case_name,
                                test_dir_name="TestUseCases",
                            ),
                            content_object=content_item,
                        )
                        for test_use_case_name in content_item.test_use_case_names
                        if test_use_case_name not in pack_test_use_case_names
                    ]
                )

        return validation_results
