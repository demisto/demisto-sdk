from __future__ import annotations

from abc import ABC

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)

ContentTypes = Script


class DuplicatedScriptNameValidator(BaseValidator, ABC):
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
