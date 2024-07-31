from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Tab(BaseStrictModel):
    name: Optional[str] = None
    new_button_definition_id: Optional[str] = Field(None, alias="newButtonDefinitionId")
    table_view: Optional[bool] = Field(None, alias="tableView")
    table_view_widget_groups: Optional[List[str]] = Field(
        None, alias="tableViewWidgetGroups"
    )
    table_view_columns: Optional[List[str]] = Field(None, alias="tableViewColumns")
    dashboard: Optional[Any] = None


class View(BaseStrictModel):
    icon: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    id_: str = Field(alias="id")
    tabs: Optional[List[Tab]] = None


class _StrictGenericModule(BaseStrictModel):
    id_: str = Field(alias="id")
    version: int
    locked: Optional[bool] = None
    system: Optional[bool] = None
    name: str
    from_version: Optional[str] = Field(None, alias="fromVersion")
    definition_ids: List[str] = Field(None, alias="definitionIds")
    views: List[View]


StrictGenericModule = create_model(
    model_name="StrictGenericModule",
    base_models=(
        _StrictGenericModule,
        NAME_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
