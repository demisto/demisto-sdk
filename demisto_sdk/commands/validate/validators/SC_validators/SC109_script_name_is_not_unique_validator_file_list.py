from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.common.tools import replace_incident_to_alert
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator import (
    DuplicatedScriptNameValidator
)

ContentTypes = Script


class DuplicatedScriptNameValidatorFileList(DuplicatedScriptNameValidator, BaseValidator[ContentTypes]):
    expected_execution_mode = [ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """
        Validate that there are no duplicate names of scripts
        when the script name included `alert`.
        """
        file_paths_to_objects = {
            str(content_item.path.relative_to(CONTENT_PATH)): content_item
            for content_item in content_items
        }
        query_results = self.graph.get_duplicate_script_name_included_incident(
            list(file_paths_to_objects)
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
