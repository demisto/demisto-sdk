from typing import Dict, Literal, Optional

from pydantic import Field, constr, root_validator

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class AssetType(BaseStrictModel):
    type: Literal["string", "int", "float", "datetime", "boolean"] = Field(
        description="Type of the asset"
    )
    is_array: bool = Field(description="Whether the asset is an array")
    field_description: Optional[constr(strip_whitespace=True, min_length=1)] = Field(  # type:ignore[valid-type]
        None, description="Description of the field"
    )


class StrictModelingRuleSchema(BaseStrictModel):
    __root__: Optional[Dict[constr(regex=r".+"), Dict[str, AssetType]]] = None  # type:ignore[valid-type]

    @root_validator(pre=True)
    def validate_and_remove_dataset_description(cls, values):
        """
        Validates the optional dataset description of each dataset (must be a non-empty string)
        and removes it, so the remaining keys of the dataset are validated as fields.
        """
        datasets = values.get("__root__")
        if not isinstance(datasets, dict):
            return values
        invalid_datasets = []
        stripped_datasets = {}
        for dataset_name, dataset in datasets.items():
            if isinstance(dataset, dict) and "dataset_description" in dataset:
                description = dataset["dataset_description"]
                if not isinstance(description, str) or not description.strip():
                    invalid_datasets.append(dataset_name)
                dataset = {
                    key: value
                    for key, value in dataset.items()
                    if key != "dataset_description"
                }
            stripped_datasets[dataset_name] = dataset
        if invalid_datasets:
            raise ValueError(
                "The field dataset_description must be a non-empty string "
                f"in the following datasets: {', '.join(invalid_datasets)}"
            )
        return {**values, "__root__": stripped_datasets}
