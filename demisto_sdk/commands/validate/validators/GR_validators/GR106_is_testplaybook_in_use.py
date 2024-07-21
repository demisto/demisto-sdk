
from __future__ import annotations

from abc import ABC

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, TestPlaybook]


class IsTestPlaybookInUseValidator(BaseValidator[ContentTypes]):
    error_code = "GR106"
    description = "validate TPB"
    rationale = ""
    error_message = "make sure to link the TPB to content item"
    related_field = "is_test"
    is_auto_fixable = False

    
    def is_valid_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        

    
