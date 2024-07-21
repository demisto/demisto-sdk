from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import IncidentFieldType
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
)
from demisto_sdk.commands.content_graph.strict_objects.common import create_model
from demisto_sdk.commands.content_graph.strict_objects.indicator_field import (
    StrictIndicatorField,
)


class _Aliases(BaseStrictModel):
    cli_name: str = Field(..., alias="cliName")
    name: str
    type_: IncidentFieldType = Field(..., alias="type")


Aliases = create_model(model_name="Aliases", base_models=(_Aliases, NAME_DYNAMIC_MODEL))


class StrictIncidentField(StrictIndicatorField):  # type:ignore
    """
    This class inherits from StrictIndicatorField, since the other class is contained in this class.
    """

    pretty_name: Optional[str] = Field(None, alias="prettyName")
    run_script_after_inc_update: Optional[bool] = Field(
        None, alias="runScriptAfterIncUpdate"
    )
    extract_indicator_types_ids: Optional[Any] = Field(
        None, alias="extractIndicatorTypesIDs"
    )
    is_extracting_specific_indicator_types: Optional[bool] = Field(
        None, alias="isExtractingSpecificIndicatorTypes"
    )
    template: Optional[str] = None
    aliases: Optional[List[Aliases]] = Field(  # type:ignore[valid-type]
        None, alias="Aliases"
    )
    x2_fields: Optional[str] = None
    alias_to: Optional[str] = Field(None, alias="aliasTo")
