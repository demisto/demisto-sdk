from __future__ import annotations

from typing import Iterable, List, Set, Union

from demisto_sdk.commands.common.tools import get_compliant_polices
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsValidCompliantPolicyNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA112"
    description = "Validator to ensure compliant policy names in Integrations and Scripts match those defined in the Config/compliant_policies.json file."
    rationale = "Enforce consistent and predefined compliant policy naming conventions across relevant content items."
    error_message = "Invalid compliant policy names: {0} were found in {1}. Please use one of the defined policy names for the 'compliantpolicies' YAML key found in Config/compliant_policies.json."
    related_field = "compliantpolicies"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        valid_compliant_policy_names: Set[str] = self._get_valid_policy_names()

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    invalid_policy_names,
                    content_item.path,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_policy_names := self.get_invalid_compliant_policies(
                    content_item, valid_compliant_policy_names
                )
            )
        ]

    def _get_valid_policy_names(self) -> Set[str]:
        """
        Get the set of valid compliant policy names from the "Config/compliant_policies.json" in Content repository.

        Returns:
            Set of existing policy names
        """
        compliant_policies_list: list[dict] = get_compliant_polices()
        return {
            policy.get("name", "")
            for policy in compliant_policies_list
            if policy.get("name")
        }

    def get_invalid_compliant_policies(
        self, content_item: ContentTypes, valid_compliant_policy_names: Set[str]
    ) -> list[str]:
        """
        Check if a content item (Integration or Script) contains invalid compliant policy names.

        Args:
            content_item: The Integration or Script object to check
            valid_compliant_policy_names: Set of valid compliant policy names

        Returns:
            list[str]: A sorted list of invalid policy names found in the content item
        """
        all_policies = set()

        if isinstance(content_item, Integration):
            for command in content_item.commands:
                if command.compliantpolicies:
                    all_policies.update(command.compliantpolicies)
        elif content_item.compliantpolicies:  # Script
            all_policies.update(content_item.compliantpolicies)

        # Use set difference to find invalid policies efficiently
        return sorted(list(all_policies - valid_compliant_policy_names))
