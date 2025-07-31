from __future__ import annotations

from abc import ABC

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Script

AGGREGATED_SCRIPTS_NAME = "Aggregated Scripts"


class MandatoryGenericArgumentsAggregatedScriptValidator(BaseValidator[ContentTypes], ABC):
    error_code = "SC101"
    description = (
        "Checks if aggregated script has mandatory generic arguments."
    )
    rationale = "Aggregated scripts should have mandatory generic arguments, this standardization ensures that."
    error_message = "Missing argument {0} in aggregated script {1}."
    related_field = "args"

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for script in content_items:
            if script.pack.name == AGGREGATED_SCRIPTS_NAME:
                if not any(arg.name == "verbose" for arg in script.args):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format("verbose", script.name),
                            content_object=script
                        )
                    )
                if not any(arg.name == "brands" for arg in script.args):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format("brands", script.name),
                            content_object=script
                        )
                    )


        return invalid_content_items
