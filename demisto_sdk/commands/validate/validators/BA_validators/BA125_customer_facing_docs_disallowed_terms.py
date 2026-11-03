from __future__ import annotations

from typing import Dict, Iterable, List, Union

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

disallowed_terms = [  # These terms are checked regardless for case (case-insensitive)
    "test-module",
    "test module",
    "long-running-execution",
]


class CustomerFacingDocsDisallowedTermsValidator(BaseValidator[ContentTypes]):
    error_code = "BA125"
    description = "Validate that customer facing docs and fields don't contain any internal terms that aren't clear for customers."
    rationale = "Ensure customer-facing docs avoid internal terms for clarity."
    error_message = "Found internal terms in a customer-facing documentation: found {terms} in {file_name}. To ignore, add this file to the .pack-ignore of pack '{pack_name}'."
    related_field = ""
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.README,
        RelatedFileType.DESCRIPTION_File,
        RelatedFileType.RELEASE_NOTE,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            found_terms: Dict[str, List[str]] = {}
            self.find_disallowed_terms(
                self.get_related_files(content_item), found_terms
            )
            for file_name, terms in found_terms.items():
                pack_name = file_name.split("/")[1]
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            file_name=file_name,
                            pack_name=pack_name,
                            terms=", ".join(terms),
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def find_disallowed_terms(self, related_files, found_terms):
        for file in related_files:
            file_content = file.file_content.casefold()
            terms = [term for term in disallowed_terms if term in file_content]
            if terms:
                # Extract the filename from the file path
                filename = "/".join(
                    file.file_path.parts[file.file_path.parts.index("Packs") :]
                )
                found_terms[f"{filename}"] = terms
        return found_terms

    def get_related_files(self, content_item):
        if content_item.content_type == "Script" and content_item.is_llm:
            return []
        related_files = [content_item.readme]
        if isinstance(content_item, Integration):
            related_files.append(content_item.description_file)
        elif isinstance(content_item, Pack):
            related_files.append(content_item.release_note)
        return related_files
