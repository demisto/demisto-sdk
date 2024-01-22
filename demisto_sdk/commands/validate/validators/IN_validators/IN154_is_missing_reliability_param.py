from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    FEED_RELIABILITY,
    RELIABILITY_PARAM,
    RELIABILITY_PARAMETER_NAMES,
    REPUTATION_COMMAND_NAMES,
)
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingReliabilityParamValidator(BaseValidator[ContentTypes]):
    error_code = "IN154"
    description = "Validate that feed integration and integrations with reputation commands have a reliability param."
    error_message = "Feed integrations and integrations with reputation commands must implement a reliability parameter, make sure to add one."
    fix_message = "Added the reliability param to the integration."
    related_field = "isfeed, configuration, script.commands"
    is_auto_fixable = True

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

    def fix(self, content_item: ContentTypes) -> FixResult:
        param: Parameter = Parameter(**RELIABILITY_PARAM)
        if content_item.is_feed:
            param.name = FEED_RELIABILITY
        content_item.params.append(param)
        return FixResult(
            validator=self,
            message=self.fix_message.format(),
            content_object=content_item,
        )
