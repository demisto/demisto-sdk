
from __future__ import annotations
import pathlib
import re

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Playbook


class IsInputKeyNotInTasksValidator(BaseValidator[ContentTypes]):
    error_code = "PB118"
    description = "Validate that all inputs described in the playbooks input section are used in tasks."
    error_message = "The playbook '{playbook_name}' contains inputs that are not used in any of its tasks: {inputs_not_in_use} "
    fix_message = ""
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]


    def collect_all_inputs_in_use(self, content_item:Playbook) -> set[str]:
        """
        Args:
            - content_item (Playbook): The content item to collect inputs from.
        Returns:
            - Set of all inputs used in playbook.
        """
        result: set = set()
        playbook_text = pathlib.Path(str(content_item.path)).read_text()
        all_inputs_occurrences = re.findall(r"inputs\.[-\w ?!():]+", playbook_text)
        for input in all_inputs_occurrences:
            input = input.strip()
            splitted = input.split(".")
            if len(splitted) > 1 and splitted[1] and not splitted[1].startswith(" "):
                result.add(splitted[1])
        return result
    
    
    def collect_all_inputs_from_inputs_section(self, content_item: Playbook) -> set[str]:
        """
        Args:
            - content_item (Playbook): The content item to collect inputs from.
        Returns:
            - A set of all inputs defined in the 'inputs' section of playbook.
        """
        inputs: dict = content_item.data.get("inputs", {})
        inputs_keys = [input["key"].strip() for input in inputs if input["key"]]
        return set(inputs_keys)
    
    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """Check whether all playbook inputs (defined in the "inputs" section) are in use in any of the tasks
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            inputs_in_use =  self.collect_all_inputs_in_use(content_item)
            inputs_in_section = self.collect_all_inputs_from_inputs_section(content_item)

            if inputs_not_in_use := inputs_in_section.difference(inputs_in_use):
                results.append(ValidationResult(
                validator=self,
                message=self.error_message.format(
                            playbook_name=content_item.name,
                            inputs_not_in_use=', '.join(inputs_not_in_use)
                        ),
                content_object=content_item
                ))
        return results
