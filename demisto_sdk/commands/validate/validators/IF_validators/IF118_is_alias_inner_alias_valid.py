from __future__ import annotations

from typing import Iterable

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField


class IsAliasInnerAliasValidator(BaseValidator[ContentTypes]):
    error_code = "IF118"
    description = "Checks for aliases that are themselves aliases."
    rationale = "An alias should not itself be an alias."
    error_message = "The following aliases have inner aliases: {aliases}"
    related_field = "Aliases"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> list[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(aliases=", ".join(aliases)),
                content_object=content_item,
            )
            for content_item in content_items
            if (aliases := get_inner_aliases(content_item.data.get("Aliases", [])))
        ]


def get_inner_aliases(aliases: list[dict]) -> list[str]:
    """Checks if any alias of the incident field is itself an alias.

    Args:
        aliases (list[dict]): The list of alias objects.

    Returns:
        list[str]: A list of the names of aliases that have their own aliases.
    """
    return [
        str(alias.get("cliName") or alias.get("cliname"))
        for alias in aliases
        if "aliases" in alias
    ]
