from __future__ import annotations

from typing import Dict, Iterable, List, Union

from demisto_sdk.commands.common.tools import search_substrings_by_line
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

DISALLOWED_PHRASES = ["BSD", "MIT", "Copyright", "proprietary"]
ContentTypes = Union[Integration, Script]


class IsPyFileContainCopyRightSectionValidator(BaseValidator[ContentTypes]):
    error_code = "BA119"
    description = "Validate that the python file doesn't have a copyright section with the words - BSD, MIT, Copyright, proprietary."
    rationale = "Content in the Cortex marketplace is licensed under the MIT license."
    error_message = "The file contains copyright key words (BSD, MIT, Copyright, proprietary) in line(s): {0}."
    related_field = "Python code file, Python test code file."
    related_file_type = [RelatedFileType.CODE_FILE, RelatedFileType.TEST_CODE_FILE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.type == "python" and (
                malformed_files := self.get_malformed_files(content_item)
            ):
                for malformed_file, malformed_lines in malformed_files.items():
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                ", ".join(malformed_lines)
                            ),
                            content_object=content_item,
                            path=content_item.code_file.file_path
                            if malformed_file == "code file"
                            else content_item.test_code_file.file_path,
                        )
                    )
        return validation_results

    def get_malformed_files(self, content_item: ContentTypes) -> Dict[str, List[str]]:
        malformed_files = {}
        if "CommonServerPython" in content_item.name:
            return {}

        for nickname, file in (
            ("code file", content_item.code_file),
            ("test code file", content_item.test_code_file),
        ):
            if file.exist and (
                invalid_lines := search_substrings_by_line(
                    phrases_to_search=DISALLOWED_PHRASES,
                    search_whole_word=True,
                    text=file.file_content,
                )
            ):
                malformed_files[nickname] = invalid_lines

        return malformed_files
