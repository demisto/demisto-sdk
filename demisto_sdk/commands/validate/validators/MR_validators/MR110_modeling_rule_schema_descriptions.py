from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.modeling_rule import (
    ModelingRule,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class ModelingRuleSchemaDescriptionsValidator(BaseValidator[ContentTypes]):
    error_code = "MR110"
    description = (
        "Validates that every dataset in the schema file of a modeling rule has a non-empty dataset_description, "
        "and every field has a non-empty field_description."
    )
    rationale = (
        "Dataset and field descriptions in the schema file are displayed in the platform, "
        "so every changed modeling rule must document its datasets and fields."
    )
    error_message = (
        "The schema file is missing required descriptions (the values must not be empty). "
        "{details}"
    )
    related_field = "Schema"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA]
    expected_execution_mode = [ExecutionMode.USE_GIT]

    def get_missing_descriptions(self, content_item: ContentTypes) -> List[str]:
        """
        Returns the details of the datasets and fields in the schema file that
        are missing a description, or have an empty one.
        """
        schema_content = content_item.schema_file.file_content
        if not isinstance(schema_content, dict):
            return []

        datasets_without_description: List[str] = []
        fields_without_description: List[str] = []
        for dataset_name, dataset in schema_content.items():
            if not isinstance(dataset, dict):
                continue
            if not self.is_valid_description(dataset.get("dataset_description")):
                datasets_without_description.append(dataset_name)
            fields_without_description.extend(
                f"{dataset_name}.{field_name}"
                for field_name, field in dataset.items()
                if field_name != "dataset_description"
                and isinstance(field, dict)
                and not self.is_valid_description(field.get("field_description"))
            )

        details: List[str] = []
        if datasets_without_description:
            details.append(
                "Datasets without dataset_description: "
                f"{', '.join(datasets_without_description)}."
            )
        if fields_without_description:
            details.append(
                "Fields without field_description: "
                f"{', '.join(fields_without_description)}."
            )
        return details

    @staticmethod
    def is_valid_description(description) -> bool:
        return isinstance(description, str) and bool(description.strip())

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(details=" ".join(details)),
                content_object=content_item,
                path=content_item.schema_file.file_path,
            )
            for content_item in content_items
            if (details := self.get_missing_descriptions(content_item))
        ]
