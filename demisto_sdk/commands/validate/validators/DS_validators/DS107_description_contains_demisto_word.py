
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]


class DescriptionContainsDemistoWordValidator(BaseValidator[ContentTypes]):
    error_code = "DS107"
    description = "Check whether a description contains the word Demisto."
    rationale = "Need a disclaimer for beta integrations."
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
    ]
    related_file_type = [RelatedFileType.YML]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
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
    

    
