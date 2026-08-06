from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

INSTANCE_NAME_FIELD_ID = "instance_name"

# The canonical, verbatim instance_name field template that every connector's
# capabilities.yaml general_configurations.configurations MUST include exactly.
# Compared as a deep dict equality against the raw YAML (not the parsed model)
# so any deviation - extra keys, missing keys, or changed values - is flagged.
EXPECTED_INSTANCE_NAME_FIELD: Dict[str, Any] = {
    "id": "instance_name",
    "title": "Instance name",
    "field_type": "input",
    "metadata": {
        "connector": {
            "parameter": "instance_name",
        },
    },
    "validations": [
        {
            "trigger": "change",
            "rules": [
                {
                    "type": "pattern",
                    "value": "^[a-zA-Z0-9 _-]+$",
                    "message": (
                        "Only alphanumeric characters, spaces, underscores, "
                        "and hyphens are allowed."
                    ),
                },
                {
                    "type": "async",
                    "validation_type": "uniqueness",
                },
            ],
        },
    ],
    "options": {
        "placeholder": "Enter a unique name for this instance",
        "create_modifiers": {
            "required": True,
            "read_only": False,
            "hidden": False,
        },
        "edit_modifiers": {
            "required": True,
            "read_only": False,
            "hidden": False,
        },
    },
}


class IsInstanceNameTemplateValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO109"
    description = (
        "Validates that capabilities.yaml general_configurations.configurations "
        "includes the verbatim instance_name field template."
    )
    rationale = (
        "Every connector must expose the standardized instance_name field so "
        "the platform can uniquely name and validate each instance. The field "
        "is a fixed template - it must appear exactly as specified, with no "
        "additions, omissions, or value changes."
    )
    error_message = (
        "Connector '{connector_id}' capabilities general_configurations is "
        "missing the verbatim instance_name field template or it does not "
        "match exactly: {details}."
    )
    related_field = "general_configurations.configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            file_content = connector.capabilities_file.file_content
            if not file_content:
                # No capabilities.yaml - nothing to validate here.
                continue

            details = self._find_template_problem(file_content)
            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details=details,
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

    def _find_template_problem(self, file_content: Dict[str, Any]) -> Optional[str]:
        """Return a human-readable problem string, or None when the verbatim
        instance_name template is present exactly."""
        general_configurations = file_content.get("general_configurations") or {}
        configurations = general_configurations.get("configurations") or []

        instance_name_field: Optional[Dict[str, Any]] = None
        for field_group in configurations:
            for field in field_group.get("fields", []) or []:
                if field.get("id") == INSTANCE_NAME_FIELD_ID:
                    instance_name_field = field
                    break
            if instance_name_field is not None:
                break

        if instance_name_field is None:
            return (
                "no instance_name field found in "
                "general_configurations.configurations"
            )

        if instance_name_field != EXPECTED_INSTANCE_NAME_FIELD:
            return (
                "the instance_name field does not match the required verbatim "
                "template"
            )

        return None
