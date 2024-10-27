from typing import Dict, Literal, Optional

from pydantic import Field, constr

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class AssetType(BaseStrictModel):
    type: Literal["string", "int", "float", "datetime", "boolean"] = Field(
        description="Type of the asset"
    )
    is_array: bool = Field(description="Whether the asset is an array")


class StrictModelingRuleSchema(BaseStrictModel):
    __root__: Optional[Dict[constr(regex=r".+"), Dict[str, AssetType]]] = None  # type:ignore[valid-type]
