from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    RELIABILITY_PARAMETER_NAMES,
    REPUTATION_COMMAND_NAMES,
)
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingReliabilityParamValidator(BaseValidator[ContentTypes]):
    error_code = "IN154"
    description = "Validate that feed integration and integrations with reputation commands have a reliability param."
    rationale = (
        "The reliability parameter is required to set indicator's reliability. "
        "For more info see, https://xsoar.pan.dev/docs/integrations/feeds#required-parameters"
    )
    error_message = "Feed integrations and integrations with reputation commands must implement a reliability parameter, make sure to add one."
    related_field = "isfeed, configuration, script.commands"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(),
                content_object=content_item,
            )
            for content_item in content_items
            if not self.is_containing_reliability_param(content_item.params)
            and self.should_contain_reliability_param(content_item)
        ]

    def is_containing_reliability_param(self, params: List[Parameter]):
        yml_config_names = [param.name.casefold() for param in params]
        return any(
            reliability_parameter_name.casefold() in yml_config_names
            for reliability_parameter_name in RELIABILITY_PARAMETER_NAMES
        )

    def should_contain_reliability_param(self, content_item: ContentTypes):
        return content_item.is_feed or any(
            [
                command.name in REPUTATION_COMMAND_NAMES
                for command in content_item.commands
            ]
        )
