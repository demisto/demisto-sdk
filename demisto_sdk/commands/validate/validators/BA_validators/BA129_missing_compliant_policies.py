
from __future__ import annotations

from typing import Iterable, List, Set, Union

from demisto_sdk.commands.common.constants import GitStatuses,PARTNER_SUPPORT,COMMUNITY_SUPPORT
from demisto_sdk.commands.common.tools import get_compliant_polices
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script]


class MissingCompliantPoliciesValidator(BaseValidator[ContentTypes]):
    error_code = "BA129"
    description = "Ensures that commands declare the appropriate compliantpolicies when using policy arguments."
    rationale = "Certain command arguments are associated with compliance policies. This validation ensures that commands using such arguments explicitly declare the relevant policies in their YAML definition."
    error_message = "{0} uses the arguments {1}, which are associated with one or more compliance policies, but does not declare the required compliantpolicies: {2}."
    related_field = "compliantpolicies"
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """
        Identify commands that use arguments associated with compliance policies
        but do not declare the required compliantpolicies.

        Args:
            content_items (Iterable[Integration | Script]):
                Content graph items to validate.
            validate_all_files (bool):
                Indicates whether validation is running on all files or only on
                files affected by the current git diff.

        Returns:
            List[ValidationResult]:
                Validation results for commands missing required compliantpolicies.
        """
        results: list[ValidationResult] = []
        argument_to_policies = self._get_argument_to_policies_map()

        for content_item in content_items:
            for command in self._get_commands(content_item):
                argument_names: Set[str] = {
                    arg.name for arg in (command.args or []) if arg.name
                }
                declared_policies = set(command.compliantpolicies or [])

                problematic_arguments: Set[str] = set()
                missing_policy_options: Set[str] = set()

                for arg in argument_names:
                    valid_policy_options = argument_to_policies.get(arg, set())

                    if not valid_policy_options:
                        continue
                    if valid_policy_options.isdisjoint(declared_policies):
                        problematic_arguments.add(arg)
                        missing_policy_options.update(valid_policy_options)

                if problematic_arguments:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                f"Command {command.name}" if isinstance(content_item, Integration) else command.name,
                                problematic_arguments,
                                missing_policy_options,
                            ),
                            content_object=content_item,
                            related_field=f"commands.{command.name}.compliantpolicies",
                        )
                    )

        return results

    @staticmethod
    def _get_commands(content_item: ContentTypes):
        """
        Extract commands from an Integration or Script content item.
        """
        if isinstance(content_item, Integration):
            return content_item.commands or []
        elif isinstance(content_item, Script):
            return [content_item]
        return []

    @staticmethod
    def _get_argument_to_policies_map() -> dict[str, set[str]]:
        """
        Build a mapping of argument names to compliance policy names
        based on Config/compliant_policies.json.
        """
        argument_to_policies: dict[str, set[str]] = {}

        for policy in get_compliant_polices():
            policy_name = policy.get("name")
            if not policy_name:
                continue

            for arg in policy.get("arguments", []):
                argument_to_policies.setdefault(arg, set()).add(policy_name)

        return argument_to_policies
