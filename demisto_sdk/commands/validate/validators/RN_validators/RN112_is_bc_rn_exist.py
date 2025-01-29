from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_dict_from_file
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsBCRNExistValidator(BaseValidator[ContentTypes]):
    error_code = "RN112"
    description = "Validate that if RN contains 'breaking change' then the breaking change release note exist and filled correctly."
    rationale = "Breaking changes should be well documented so they can pop up to users when updating versions."
    error_message = "The release notes contain information about breaking changes but missing a breaking change file, make sure to add one as {0} and that the file contains the 'breakingChanges' entry."
    related_field = "release notes"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            if "breaking change" not in content_item.release_note.file_content:
                continue
            json_path = str(content_item.release_note.file_path).replace(".md", ".json")
            if Path(json_path).exists():
                if (
                    json_file_content := get_dict_from_file(path=json_path)[0]
                ) and not json_file_content.get("breakingChanges"):
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(json_path),
                            content_object=content_item,
                            path=content_item.release_note.file_path,
                        )
                    )
            else:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(json_path),
                        content_object=content_item,
                    )
                )
        return validation_results
