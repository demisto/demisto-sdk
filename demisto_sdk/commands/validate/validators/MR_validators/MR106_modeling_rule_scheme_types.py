from __future__ import annotations

from typing import Iterable, List
import json

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.modeling_rule import (
    ModelingRule,

)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


def load_json_from_path(file_path: str):
    """
        Load JSON data from a file located at the specified path.

        Args:
            file_path (str): Path to the JSON file.

        Returns:
            dict: Parsed JSON data as a Python dictionary.
    """
    with open(file_path, 'r') as file:
        json_data = json.load(file)
    return json_data


class ModelingRuleSchemaTypesValidator(BaseValidator[ContentTypes]):
    error_code = "MR106"
    description = ""
    rationale = ""
    error_message = " {invalid_types}"
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA]

    def invalid_schema_types(self, content_item):
        """
        Validates all types used in the schema file are valid, i.e. part of the list below.
        """
        valid_types = {"string", "int", "float", "datetime", "boolean"}
        file_content = load_json_from_path(content_item.file_path)
        invalid_types = [
            attribute.get("type")
            for attributes in file_content.values()
            for attribute in attributes.values()
            if attribute.get("type") not in valid_types
        ]
        for attributes in file_content.values():
            for attribute in attributes.values():
                type_to_validate = attribute.get("type")
                if attribute.get("type") not in valid_types:
                    invalid_types.append(type_to_validate)
        return invalid_types


    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(', '.join(invalid_types)),
                content_object=content_item,
            )

            for content_item in content_items
            if (
                invalid_types := self.invalid_schema_types(content_item.schema_file)
            )
        ]
