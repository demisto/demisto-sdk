from __future__ import annotations

from typing import Iterable, List

from more_itertools import always_iterable

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField
PACKS_IGNORE = ["Common Types", "Core Alert Fields"]


class NameFieldPrefixValidator(BaseValidator[ContentTypes]):
    error_code = "IF113"
    description = "Checks if field name starts with its pack name or one of the item prefixes from pack metadata."
    rationale = "Required by the platform."
    error_message = (
        "Field name must start with the relevant pack name or one of the item prefixes found in pack metadata."
        "\nFollowing prefixes are allowed for this IncidentField:"
        "\n{allowed_prefixes}"
    )
    related_field = "name"
    expected_git_statuses = [GitStatuses.ADDED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    allowed_prefixes=", ".join(allowed_prefixes(content_item))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.pack_name not in PACKS_IGNORE
                and not is_name_using_allowed_prefix(content_item)
            )
        ]


def is_name_using_allowed_prefix(content_item: ContentTypes) -> bool:
    """
    Check if the IncidentField name begins with any of the allowed prefixes.
    """
    return any(
        content_item.name.startswith(prefix)
        for prefix in allowed_prefixes(content_item)
    )


def allowed_prefixes(content_item: ContentTypes) -> set[str]:
    """
    Collects from pack metadata all the allowed prefixes
    """
    prefixes = {content_item.pack_name}
    if not content_item.in_pack:
        return prefixes

    metadata = content_item.in_pack.pack_metadata_dict or {}
    item_prefix = metadata.get("itemPrefix")

    return prefixes | set(always_iterable(item_prefix))
