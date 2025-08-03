from __future__ import annotations

from abc import ABC

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script

AGGREGATED_SCRIPTS_NAME = "Aggregated Scripts"
AGGREGATED_SCRIPTS_MANDATORY_ARGUMENTS = ["verbose", "brands"]


class MandatoryGenericArgumentsAggregatedScriptValidator(BaseValidator[ContentTypes]):
    error_code = "SC101"
    description = (
        "Checks if aggregated script has mandatory generic arguments."
    )
    rationale = "Aggregated scripts should have mandatory generic arguments, this standardization ensures that."
    error_message = "The Aggregated Script {0} is missing the following mandatory argument{1}: {2}."
    related_field = "args"

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for script in content_items:
            if script.pack.name == AGGREGATED_SCRIPTS_NAME:
                missing_args = []
                for marg in AGGREGATED_SCRIPTS_MANDATORY_ARGUMENTS:
                    if not any(arg.name == marg for arg in script.args):
                        missing_args.append(marg)

                if missing_args:
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(script.name, "" if len(missing_args) == 1 else "s",
                                                              ", ".join(missing_args)),
                            content_object=script
                        )
                    )

        return invalid_content_items
