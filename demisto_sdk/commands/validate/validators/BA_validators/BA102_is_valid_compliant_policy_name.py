
from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Set, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import get_compliant_polices
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsValidCompliantPolicyNameValidator(BaseValidator[ContentTypes], ABC):
    error_code = "BA102"
    description = "Validator to ensure compliant policy names in Integrations and Scripts match those defined in the Config/compliant_policies.json file."
    rationale = "Enforce consistent and predefined compliant policy naming conventions across relevant content items."
    error_message = "Invalid compliant policy name(s) found for '{0}'. Please use only policy names defined in Config/compliant_policies.json."
    related_field = "compliantpolicies"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        valid_compliant_policy_names: Set[str] = self._get_valid_policy_names()

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_contains_invalid_compliant_policy_name(
                    content_item, valid_compliant_policy_names
                )
            )
        ]

    def _get_valid_policy_names(self) -> Set[str]:
        """
        Get the set of valid compliant policy names from the "Config/compliant_policies.json" in Content repository.

        Returns:
            Set of valid policy names
        """
        compliant_policies_list: list[dict] = get_compliant_polices()
        return {policy.get("name", "") for policy in compliant_policies_list if policy.get("name")}


def content_contains_invalid_compliant_policy_name(content_item: ContentTypes, valid_compliant_policy_names: Set[str]) -> bool:
    """
    Check if a content item (Integration or Script) contains invalid compliant policy names.

    Args:
        content_item: The Integration or Script object to check
        valid_compliant_policy_names: Set of valid compliant policy names

    Returns:
        bool: True if invalid policy name found, False otherwise
    """
    if isinstance(content_item, Integration):
        for command in content_item.commands:
            if compliant_policies_list := command.compliantpolicies:
                for policy in compliant_policies_list:
                    if policy not in valid_compliant_policy_names:
                        return True
    else:  # Script
        if compliant_policies_list := content_item.compliantpolicies:
            for policy in compliant_policies_list:
                if policy not in valid_compliant_policy_names:
                    return True

    return False