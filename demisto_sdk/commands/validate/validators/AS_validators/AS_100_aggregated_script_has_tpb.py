from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

class AggregatedScriptHasTPBValidator(BaseValidator[Script]):
    error_code = "AS100"
    description = "Validates that the aggregated script has a TPB"
    rationale = "Make sure aggregated scripts are tested thoroughly"

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[Script],
    ) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            if error_message := self.is_missing_tpb(content_item):
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=error_message,
                        content_object=content_item,
                    )
                )
        return invalid_content_items

    def is_missing_tpb(self, content_item: Script) -> str:
        if not content_item.tests:
            return f"Script {content_item.name} is missing a TPB"
        return  ""