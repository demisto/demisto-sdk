
from __future__ import annotations

from typing import Iterable

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = IncidentField


class IsAliasInnerAliasValidator(BaseValidator[ContentTypes]):
    error_code = "IF118"
    description = ""
    rationale = ""
    error_message = "The following aliases have inner aliases: {aliases}"
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    
    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> list[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(aliases=", ".join(aliases)),
                content_object=content_item,
            )
            for content_item in content_items
            if (aliases := self.has_inner_aliases(content_item.aliases))
        ]
    
    def has_inner_aliases(aliases: list[dict]) -> list[str]:
        return [
            alias.get("cliname")
            for alias in aliases
            if "aliases" in alias
        ]

        

    
