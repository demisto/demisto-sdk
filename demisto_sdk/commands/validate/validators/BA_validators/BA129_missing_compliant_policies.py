from __future__ import annotations

from typing import Any, Iterable, List, Optional, Set, Union

from demisto_sdk.commands.common.constants import GitStatuses
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
    error_message = "{0} uses the arguments: {1}, which are associated with one or more compliance policies, but does not declare the required compliantpolicies: {2}."
    related_field = "compliantpolicies"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """
        Identify commands that use arguments associated with compliance policies
        but do not declare the required compliantpolicies.
        Only identify newly commands.

        Args:
            content_items (Iterable[ContentTypes]): A list of Integration or Script objects to validate.

        Returns:
            List[ValidationResult]: A list of validation results for any commands failing the policy check.
        """
        results: list[ValidationResult] = []
        argument_to_policies = self._get_argument_to_policies_map()

        for content_item in content_items:
            commands_to_validate = []
            if content_item.git_status == GitStatuses.ADDED:
                commands_to_validate = self._get_commands(content_item)
            else:
                for command in self._get_commands(content_item):
                    if self._is_new_command(content_item, command.name):
                        commands_to_validate.append(command)

            for command in commands_to_validate:
                validation_result = self._check_command_compliance(
                    command, content_item, argument_to_policies
                )
                if validation_result:
                    results.append(validation_result)

        return results

    def _check_command_compliance(
        self,
        command,
        content_item: ContentTypes,
        argument_to_policies: dict[str, set[str]],
    ) -> Optional[ValidationResult]:
        """
        Helper method to validate a single command against the policy map.
        Args:
            command: The command object to validate.
            content_item (ContentTypes): The parent Integration or Script object.
            argument_to_policies (dict[str, set[str]]): A map with argument names to their required policies.

        Returns:
            Optional[ValidationResult]: A ValidationResult if the command is non-compliant, otherwise None.
        """
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
            # Check if the declared policies cover the requirements for this arg
            if valid_policy_options.isdisjoint(declared_policies):
                problematic_arguments.add(arg)
                missing_policy_options.update(valid_policy_options)

        if problematic_arguments:
            return ValidationResult(
                validator=self,
                message=self.error_message.format(
                    f"Command {command.name}"
                    if isinstance(content_item, Integration)
                    else command.name,
                    sorted(problematic_arguments),
                    sorted(missing_policy_options),
                ),
                content_object=content_item,
                related_field=f"commands.{command.name}.compliantpolicies",
            )
        return None

    def _is_new_command(self, content_item: ContentTypes, command_name: str) -> bool:
        """
        Check if the given command is new command.
        Args:
            content_item (ContentTypes): The current content item.
            command_name (str): The name of the command to look up.

        Returns:
            bool: wether the command is new.
        """
        old_content_item = content_item.old_base_content_object
        if not old_content_item:
            return True

        if isinstance(old_content_item, Script):
            return old_content_item.name != command_name

        if isinstance(old_content_item, Integration):
            for command in old_content_item.commands:
                if command.name == command_name:
                    return False

        return True

    @staticmethod
    def _get_commands(content_item: ContentTypes) -> List[Any]:
        """
        Extracts the list of command objects from the content item.

        For Integrations, this returns the list of defined commands.
        For Scripts, which act as a single command, this returns a list containing the script object itself.

        Args:
            content_item (ContentTypes): The Integration or Script object.

        Returns:
            List[Any]: A list of command objects to be validated.
        """
        if isinstance(content_item, Integration):
            return content_item.commands or []
        elif isinstance(content_item, Script):
            return [content_item]
        return []

    @staticmethod
    def _get_argument_to_policies_map() -> dict[str, set[str]]:
        """
        Builds a lookup mapping of argument names to their associated compliance policies.

        It iterates through the compliant policies configuration (retrieved via `get_compliant_polices`)
        and maps every argument listed in a policy to the policy's name. This allows for easy
        lookup to check if an argument requires specific compliance policies.

        Returns:
            dict[str, set[str]]: A dictionary where keys are argument names and values are sets of policy names associated with that argument.
        """
        argument_to_policies: dict[str, set[str]] = {}
        for policy in get_compliant_polices():
            policy_name = policy.get("name")
            if not policy_name:
                continue
            for arg in policy.get("arguments", []):
                argument_to_policies.setdefault(arg, set()).add(policy_name)
        return argument_to_policies
