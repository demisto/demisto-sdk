from __future__ import annotations

from abc import ABC

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Script


class MandatoryGenericArgumentsAggregatedScriptValidator(BaseValidator[ContentTypes], ABC):
    error_code = "SC101"
    description = (
        "Checks if aggregated script has mandatory generic arguments."
    )
    rationale = "Aggregated scripts should have mandatory generic arguments, this standardization ensures that."
    error_message = "Missing argument {0} in aggregated script {1}."
    fix_message = "Add argument {0} to aggregated script {1}."
    related_field = "args"

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            if content_item.path.parent.name == "Packs/AggregatedScripts":
                if not any(arg.name == "verbose" for arg in content_item.args):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format("verbose", content_item.name),
                            content_object=content_item
                        )
                    )
                if not any(arg.name == "brands" for arg in content_item.args):
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format("brands", content_item.name),
                            content_object=content_item
                        )
                    )


        return invalid_content_items
