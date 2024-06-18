from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class ModelingRuleSchemaTypesValidator(BaseValidator[ContentTypes]):
    error_code = "MR106"
    description = ""
    rationale = ""
    error_message = " {invalid_types}"
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.SCHEMA]

    def invalid_schema_types(self, content_item):
        """
        Validates all types used in the schema file are valid, i.e. part of the list below.
        """
        valid_types = {"string", "int", "float", "datetime", "boolean"}
        invalid_types = []
        if content_item:
            for dataset in content_item:
                attributes = content_item.get(dataset)
                for attr in attributes.values():
                    type_to_validate = attr.get("type")
                    if type_to_validate not in valid_types:
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
