
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Playbook


class IsInputKeyNotInTasksValidator(BaseValidator[ContentTypes]):
    error_code = "PB118"
    description = ""
    error_message = ""
    fix_message = ""
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    
    def collect_all_inputs_from_inputs_section(self) -> Set[str]:
        """

        Returns: A set of all inputs defined in the 'inputs' section of playbook.

        """
        inputs: Dict = self.current_file.get("inputs", {})
        inputs_keys = []
        for input in inputs:
            if input["key"]:
                inputs_keys.append(input["key"].strip())
        return set(inputs_keys)
    
     def collect_all_inputs_in_use(self) -> Set[str]:
        """

        Returns: Set of all inputs used in playbook.

        """
        result: set = set()
        with open(self.file_path) as f:
            playbook_text = f.read()
        all_inputs_occurrences = re.findall(r"inputs\.[-\w ?!():]+", playbook_text)
        for input in all_inputs_occurrences:
            input = input.strip()
            splitted = input.split(".")
            if len(splitted) > 1 and splitted[1] and not splitted[1].startswith(" "):
                result.add(splitted[1])
        return result
    
    def inputs_in_use_check(self, is_modified: bool) -> bool:
        """

        Args:
            is_modified: Wether the given files are modified or not.

        Returns:
            True if both directions for input use in playbook passes.

        """
        
        inputs_in_use: set = self.collect_all_inputs_in_use()
        inputs_in_section: set = self.collect_all_inputs_from_inputs_section()
        all_inputs_in_use = self.are_all_inputs_in_use(inputs_in_use, inputs_in_section)
        are_all_used_inputs_in_inputs_section = (
            self.are_all_used_inputs_in_inputs_section(inputs_in_use, inputs_in_section)
        )
        return all_inputs_in_use and are_all_used_inputs_in_inputs_section
    
    
     def are_all_inputs_in_use(self, inputs_in_use: set, inputs_in_section: set) -> bool:
        """Check whether the playbook inputs are in use in any of the tasks

        Return:
            bool. if the Playbook inputs are in use.
        """

        inputs_not_in_use = inputs_in_section.difference(inputs_in_use)

        if inputs_not_in_use:
            playbook_name = self.current_file.get("name", "")
            error_message, error_code = Errors.input_key_not_in_tasks(
                playbook_name, sorted(inputs_not_in_use)
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True
    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        for content_item in content_items:
            
        
    return ValidationResult(
