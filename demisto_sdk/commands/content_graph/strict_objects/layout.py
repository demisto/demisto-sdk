from typing import Any, Optional, Sequence

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    ID_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _FieldSchema(BaseStrictModel):
    id: Optional[str] = None
    version: Optional[int] = None
    modified: Optional[str] = None
    field_id: Optional[str] = Field(None, alias="fieldId")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    sort_values: Optional[str] = Field(None, alias="sortValues")


FieldSchema = create_model(
    model_name="FieldSchema", base_models=(_FieldSchema, ID_DYNAMIC_MODEL)
)


class _Section(BaseStrictModel):
    id: Optional[str] = None
    version: Optional[int] = None
    modified: Optional[str] = None
    name: Optional[str] = None
    type_: Optional[str] = Field(None, alias="type")
    is_visible: Optional[bool] = Field(None, alias="isVisible")
    read_only: Optional[bool] = Field(None, alias="readOnly")
    description: Optional[str] = None
    query: Optional[Any] = None
    query_type: Optional[Any] = Field(None, alias="queryType")
    sort_values: Optional[str] = Field(None, alias="sortValues")
    fields: Optional[Sequence[FieldSchema]] = None  # type:ignore[valid-type]


Section = create_model(
    model_name="Section",
    base_models=(
        _Section,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        ID_DYNAMIC_MODEL,
    ),
)


class _Layout(BaseStrictModel):
    id_: str = Field(..., alias="id")
    system: Optional[bool] = None
    type_name: Optional[str] = Field(None, alias="TypeName")
    version: Optional[int] = None
    kind: Optional[str] = None
    type_id: str = Field(..., alias="typeId")
    modified: Optional[str] = None
    name: Optional[str] = None
    tabs: Optional[Any] = None
    sections: Optional[Sequence[Section]] = None  # type:ignore[valid-type]


Layout = create_model(
    model_name="Layout", base_models=(_Layout, NAME_DYNAMIC_MODEL, ID_DYNAMIC_MODEL)
)


class _StrictLayout(BaseStrictModel):
    type_id: str = Field(..., alias="typeId")
    type_name: Optional[str] = Field(None, alias="TypeName")
    version: Optional[int] = None
    kind: str
    from_version: Optional[str] = Field(None, alias="fromVersion")
    to_version: str = Field(..., alias="toVersion")
    system: Optional[bool] = None
    description: Optional[str] = None
    id_: Optional[str] = Field(None, alias="id")
    layout: Optional[Layout] = None  # type:ignore[valid-type]
    definition_id: Optional[str] = Field(None, alias="definitionId")


StrictLayout = create_model(
    model_name="StrictLayout",
    base_models=(_StrictLayout, DESCRIPTION_DYNAMIC_MODEL, ID_DYNAMIC_MODEL),
)
