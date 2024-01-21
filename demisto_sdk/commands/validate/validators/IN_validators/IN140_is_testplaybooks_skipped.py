from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsTestplaybooksSkippedValidator(BaseValidator[ContentTypes]):
    error_code = "IN140"
    description = (
        "Validate that there're no skipped test playbooks for the given integration."
    )
    error_message = "The integration {0} is currently in skipped. Please add working tests and unskip.{1}"
    related_field = "tests"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        with open(CONF_PATH) as data_file:
            skipped_integrations = json.load(data_file).get("skipped_integrations", {})
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.object_id,
                    f' skipped comment: {skipped_integrations.get(content_item.object_id), ""}'
                    if skipped_integrations.get(content_item.object_id, "")
                    else "",
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.object_id in skipped_integrations
            and "no instance" in skipped_integrations[content_item.object_id].lower()
            and not content_item.has_unittests
        ]
