from __future__ import annotations

from typing import Dict, Iterable, List, Union

from demisto_sdk.commands.common.tools import check_text_content_contain_sub_text
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsPyFileContainCopyRightSectionValidator(BaseValidator[ContentTypes]):
    error_code = "BA119"
    description = "Validate that the python file doesn't have a copyright section with the words - BSD, MIT, Copyright, proprietary."
    rationale = "Content in the Cortex marketplace is licensed under the MIT license."
    error_message = "Invalid keywords related to Copyrights (BSD, MIT, Copyright, proprietary) were found in lines:\n{0}"
    related_field = "Python code file, Python test code file."
    related_file_type = [RelatedFileType.CODE_FILE, RelatedFileType.TEST_CODE_FILE]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The {file} contains copyright key words in line(s) {', '.join(malformed_lines)}."
                            for file, malformed_lines in malformed_files.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.type == "python"
            and (malformed_files := self.get_malformed_files(content_item))
        ]

    def get_malformed_files(self, content_item: ContentTypes) -> Dict[str, List[str]]:
        malformed_files = {}
        if "CommonServerPython" in content_item.name:
            return {}
        if content_item.code_file.exist and (
            invalid_lines := check_text_content_contain_sub_text(
                sub_text_list=["BSD", "MIT", "Copyright", "proprietary"],
                to_split=True,
                text=content_item.code_file.file_content,
            )
        ):
            malformed_files["code file"] = invalid_lines
        if content_item.test_code_file.exist and (
            invalid_lines := check_text_content_contain_sub_text(
                sub_text_list=["BSD", "MIT", "Copyright", "proprietary"],
                to_split=True,
                text=content_item.test_code_file.file_content,
            )
        ):
            malformed_files["test code file"] = invalid_lines
        return malformed_files
