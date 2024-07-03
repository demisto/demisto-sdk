from typing import Iterable, List

from pydantic import error_wrappers

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration, StrictCommand, StrictIntegration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class SchemeValidator(BaseValidator[ContentTypes]):
    error_code = "ST110"
    description = (
        "Validate that the scheme's structure is valid."
    )
    error_message = "Filed can't contain None, must be valuable."
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.subtype,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_content_item_contain_none(content_item)
        ]

    def is_content_item_contain_none(self, content_item) -> bool:
        try:
            content_item.commands = [StrictCommand.cast(command) for command in content_item.commands]
            StrictIntegration.cast(content_item)
        except error_wrappers.ValidationError:
            return True
        return False


integraion = Integration(id=1, node_id=1, marketplaces=["xsoar"], path="", name="",
                         fromversion="", toversion="", display_name="", deprecated=False, type="", category="")

validation_result = SchemeValidator().is_valid(content_items=[integraion])
print(validation_result)  # you can debug here and see the validation result