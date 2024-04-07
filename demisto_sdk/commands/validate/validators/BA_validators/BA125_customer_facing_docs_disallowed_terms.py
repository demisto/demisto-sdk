
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]

disallowed_terms = (
        [  # These terms are checked regardless for case (case-insensitive)
            "test-module",
            "test module",
            "long-running-execution",
        ]
    )


class CustomerFacingDocsDisallowedTermsValidator(BaseValidator[ContentTypes]):
    error_code = "BA125"
    description = "Validate that customer facing docs and fields don't contain any internal terms that aren't clear for customers."
    rationale = "Ensure customer-facing docs avoid internal terms for clarity."
    error_message = "Found internal terms in a customer-facing documentation file: {terms}"
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File, RelatedFileType.RELEASE_NOTE]
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED]
    

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        found_terms = []
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(terms=', '.join(found_terms)),
                content_object=content_item,
            )
            for content_item in content_items
            if self.find_disallowed_terms(self.get_related_files(content_item), found_terms)
        ]

    def find_disallowed_terms(self, related_files, found_terms):
        for file in related_files:
            file_content = file.file_content.casefold()
            found_terms.extend([term for term in disallowed_terms if term in file_content])
        return found_terms

    def get_related_files(self, content_item):
        if isinstance(content_item, Integration):
            return [content_item.readme, content_item.description_file]
        elif isinstance(content_item, Pack):
            return [content_item.release_note, content_item.readme]
        elif isinstance(content_item, (Playbook, Script)):
            return [content_item.readme,]
        raise ValueError(f"unexpected content item type {content_item.content_type}")
