
from __future__ import annotations

from abc import ABC

from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Pack


class IsPackDisplayNameAlreadyExistsValidator(BaseValidator, ABC):
    error_code = "GR104"
    description = "Validate that there are no duplicate display names in the repo"
    rationale = " Validate the existance of duplicate display names"
    error_message = "Pack '{content_name}' has a duplicate display_name as: {pack_display_names} "
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

    def is_valid_use_graph(self, file_paths_to_objects: Iterable[str]) -> List[ValidationResult]:
        query_results = self.graph.get_duplicate_pack_display_name(
            list(file_paths_to_objects)
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_id=content_id, pack_display_names=(', '.join(duplicate_names_id))
                ),
                content_object=content_id,
            )
            for content_id, duplicate_names_id in query_results
        ]
    
