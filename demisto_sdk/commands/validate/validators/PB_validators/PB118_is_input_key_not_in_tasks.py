
from __future__ import annotations
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
    description = ""
    error_message = ""
    fix_message = ""
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            # def collect_all_inputs_in_use(self) -> Set[str]:
            result: set = set()
            with open(str(content_item.path)) as f:
                playbook_text = f.read()
            all_inputs_occurrences = re.findall(r"inputs\.[-\w ?!():]+", playbook_text)
            for input in all_inputs_occurrences:
                input = input.strip()
                splitted = input.split(".")
                if len(splitted) > 1 and splitted[1] and not splitted[1].startswith(" "):
                    result.add(splitted[1])
            inputs_in_use =  result
            
            #def collect_all_inputs_from_inputs_section(self) -> Set[str]:
            inputs: dict = content_item.data.get("inputs", {})
            inputs_keys = []
            for input in inputs:
                if input["key"]:
                    inputs_keys.append(input["key"].strip())
            inputs_in_section = set(inputs_keys)
            
            inputs_not_in_section = inputs_in_use.difference(inputs_in_section)
            if inputs_not_in_section:
                results.append(
                validator=self,
                message=self.error_message,
                content_object=content_item
                )
 
        
        return results
