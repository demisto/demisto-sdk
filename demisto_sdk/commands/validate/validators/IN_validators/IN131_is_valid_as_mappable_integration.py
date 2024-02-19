from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    GET_MAPPING_FIELDS_COMMAND_NAME,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidAsMappableIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN131"
    description = "Validate that the integration is valid as a mappable integration."
    rationale = (
        f"An integration in Cortex XSOAR/XSIAM that is marked as mappable should include the {GET_MAPPING_FIELDS_COMMAND_NAME} command. "
        "This command is essential for the mapping process as it retrieves the fields from the external system that can be mapped to Cortex XSOAR/XSIAM fields. "
        "Without this command, the integration cannot be used effectively for field mapping, which is a key functionality for incident synchronization and mirroring. "  # TODO i'm not sure about the rationale
        "For more info, visit https://xsoar.pan.dev/docs/integrations/mirroring_integration#get-mapping-fields"
    )
    error_message = f"The integration is a mappable integration and is missing the {GET_MAPPING_FIELDS_COMMAND_NAME} command. Please add the command."
    related_field = "ismappable, commands"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_mappable
            and not any(
                [
                    command.name == GET_MAPPING_FIELDS_COMMAND_NAME
                    for command in content_item.commands
                ]
            )
        ]
