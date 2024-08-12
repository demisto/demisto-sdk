from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class IsSchemaMatchXIFValidator(BaseValidator[ContentTypes]):
    error_code = "MR107"
    description = "Validate that the dataset name of a modeling rule shows in the xif and schema files match."
    rationale = "We want to make sure the datasets match between the schema and the XIF file to avoid discrepancy between the expected info and the info shown in the UI."
    error_message = "There is a mismatch between datasets in schema file and in the xif file. Either there are more datasets declared in one of the files, or the datasets titles are not the same."
    related_field = "Schema, XIF"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.SCHEMA, RelatedFileType.XIF]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not (
                (xif_datasets := content_item.xif_file.get_dataset_from_xif())
                and (
                    schema_datasets := (
                        content_item.schema_file.file_content or {}
                    ).keys()
                )
                and len(xif_datasets) == len(schema_datasets)
                and all(dataset in schema_datasets for dataset in xif_datasets)
            )
        ]
