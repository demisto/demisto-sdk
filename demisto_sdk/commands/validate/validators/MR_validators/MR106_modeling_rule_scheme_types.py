from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    SCHEMA_FILE_VALID_ATTRIBUTES_TYPE,
)
from demisto_sdk.commands.content_graph.objects.modeling_rule import (
    ModelingRule,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class ModelingRuleSchemaTypesValidator(BaseValidator[ContentTypes]):
    error_code = "MR106"
    description = (
        "Type validation in schema files verifies that each specified data type conforms to a predefined set"
        " of acceptable types"
    )
    rationale = (
        "Validating types in schema files is crucial for maintaining data integrity and compatibility across"
        " systems, preventing errors and ensuring reliable data processing."
    )
    error_message = (
        "The following types in the schema file are invalid: {invalid_types}."
        " Valid types are: string, int , float, datetime, boolean."
    )
    related_field = "Schema"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA]

    def invalid_schema_types(self, content_item):
        """
        Validates all types used in the schema file are valid, i.e. part of the list below.
        """
        schema_content = content_item.schema_file.file_content
        invalid_types = [
            f'"{attribute.get("type")}"'
            for attributes in schema_content.values()
            for attribute in attributes.values()
            if attribute.get("type") not in SCHEMA_FILE_VALID_ATTRIBUTES_TYPE
        ]
        return invalid_types

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    invalid_types=", ".join(invalid_types)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_types := self.invalid_schema_types(content_item))
        ]
