from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.tools import replace_incident_to_alert
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class DuplicatedScriptNameValidator(BaseValidator[ContentTypes], ABC):
    error_code = "SC109"
    description = (
        "Validate that there are no scripts with the same type and the same name."
    )
    rationale = "Duplicate names cause confusion and unpredictable behaviors."
    error_message = (
        "Cannot create a script with the name {0}, because a script with the name {1} already exists.\n"
        "(it will not be possible to create a new script whose name includes the word Alert/Alerts "
        "if there is already a script with a similar name and only the word Alert/Alerts "
        "is replaced by the word Incident/Incidents\nfor example: if there is a script `getIncident'"
        "it will not be possible to create a script with the name `getAlert`)"
    )
    related_field = "name"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files
    ) -> List[ValidationResult]:
        """
        Validate that there are no duplicate names of scripts
        when the script name included `alert`.
        """
        file_paths_to_objects = {
            str(content_item.path.relative_to(CONTENT_PATH)): content_item
            for content_item in content_items
        }
        query_list = list(file_paths_to_objects) if not validate_all_files else []

        query_results = self.graph.get_duplicate_script_name_included_incident(
            query_list
        )

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    replace_incident_to_alert(script_name), script_name
                ),
                content_object=file_paths_to_objects[file_path],
            )
            for script_name, file_path in query_results.items()
            if file_path in file_paths_to_objects
        ]
