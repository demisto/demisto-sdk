from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField


class NameFieldPrefixValidator(BaseValidator[ContentTypes]):
    error_code = "IF113"
    description = "Checks if field name starts with its pack name or one of the itemPrefixes from pack metadata"
    rationale = "Required by the platform."
    error_message = "Field name: {field_name} is invalid. Field name must start with the relevant pack name"
    related_field = "name"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(field_name=content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.name
                in cast(
                    List[str],
                    self.get_allowed_prefixes_for_specific_incident_field(content_item),
                )
            )
        ]

    def get_allowed_prefixes_for_specific_incident_field(
        self, content_item: ContentTypes
    ):
        """
        Collects from pack metadata all the allowed prefixes
        """
        if content_item.in_pack and (
            metadata := content_item.in_pack.pack_metadata_dict
        ):
            if not metadata.get("itemPrefix"):
                return [content_item.pack_name]
            else:
                return (
                    metadata.get("itemPrefix")
                    if isinstance(metadata.get("itemPrefix"), list)
                    else [metadata.get("itemPrefix")]
                )
        else:
            return [content_item.pack_name]
