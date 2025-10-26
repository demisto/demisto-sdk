from typing import ClassVar, Final, Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

NO_TESTS_FORMAT: Final[list[str]] = ["No tests (auto formatted)"]
MISSING_TPB_MESSAGE: Final[str] = "Script {name} is missing a TPB"
AGGREGATED_SCRIPTS_PACK_NAME: Final[str] = "Aggregated Scripts"

class AggregatedScriptHasTPBValidator(BaseValidator[Script]):
    error_code: ClassVar[str] = "AS100"
    description: ClassVar[str] = "Validates that the aggregated script has a TPB"
    rationale: ClassVar[str] = "Make sure aggregated scripts are tested thoroughly"

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[Script],
    ) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            if content_item.pack_name != AGGREGATED_SCRIPTS_PACK_NAME:
                continue
            if error_message := self.is_missing_tpb(content_item):
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=error_message,
                        content_object=content_item,
                    )
                )
        return invalid_content_items

    @staticmethod
    def is_missing_tpb(content_item: Script) -> str:
        """Check if the script is missing a test playbook.

        Args:
            content_item: The script to check.

        Returns:
            str: Error message if the script is missing a TPB, empty string otherwise.
        """
        if not content_item.tests or content_item.tests == NO_TESTS_FORMAT:
            script_name = getattr(content_item, 'name', 'Unknown')
            return MISSING_TPB_MESSAGE.format(name=script_name)
        return ""