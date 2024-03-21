
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import get_pack_name
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Pack, Playbook]


class IsReadmeExistsValidator(BaseValidator[ContentTypes]):
    error_code = "RM109"
    description = "Validates if there is a readme file for the content item."
    rationale = "Ensure that the content item contains additional information about use-cases, inputs, and outputs."
    error_message = "There is no README file for content item from type {0} in pack named '{1}'. Please add relevant README."
    related_field = "readme"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED, GitStatuses.DELETED]
    related_file_type = [RelatedFileType.README]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.content_type, get_pack_name(content_item.path)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not content_item.readme.exist
            )
        ]
    

    
