from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class FirstLevelHeaderMissingValidator(BaseValidator[ContentTypes]):
    error_code = "RN116"
    description = "Validate that the release note has either a valid first level header or a valid force header."
    rationale = "We want to enforce proper release notes structure to ensure the documentation is readable."
    error_message = 'The following RN is missing a first level header.\nTo ensure a proper RN structure, please use "demisto-sdk update-release-notes -i Packs/{0}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes'
    related_field = "Release notes"
    related_file_type = [RelatedFileType.RELEASE_NOTE]
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.path.parts[-1]),
                content_object=content_item,
                path=content_item.release_note.file_path,
            )
            for content_item in content_items
            if not re.search(r"\s#{4}\s", f"\n{content_item.release_note.file_content}")
            and not re.search(
                r"\s#{2}\s",
                f"\n{content_item.release_note.file_content}",  # We look for a first level header by either #### or ## in case force flag was used.
            )
        ]
