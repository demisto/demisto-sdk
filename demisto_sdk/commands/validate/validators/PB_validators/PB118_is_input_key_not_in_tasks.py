
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

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        # Add your validation right here
        pass
    #return vlidation_results
    

    
