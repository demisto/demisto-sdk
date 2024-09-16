from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_dict_from_file
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsBcRnExistValidator(BaseValidator[ContentTypes]):
    error_code = "RN112"
    description = "Validate that if RN contains 'breaking change' then the breaking change release note exist as well."
    rationale = "Breaking changes should be well documented and pop up to uses when updating versions."
    error_message = "The Release notes contains information about breaking changes but missing a breaking change file, make sure to add one as {0} and that the file contains the 'breakingChanges' entry."
    related_field = "release notes"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.RELEASE_NOTE]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(json_path),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                "breaking change" in content_item.release_note.file_content
                and (
                    json_path := str(content_item.release_note.file_content).replace(
                        ".md", ".json"
                    )
                )
                and (
                    json_file_content := get_dict_from_file(path=json_path)[0]
                )  # extract only the dictionary
                and not json_file_content.get("breakingChanges")
            )
        ]
