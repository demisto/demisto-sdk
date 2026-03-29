from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Tab(BaseStrictModel):
    name: Optional[str] = Field(
        None,
        description="Display name of the tab shown in the generic module UI.",
    )
    new_button_definition_id: Optional[str] = Field(
        None,
        alias="newButtonDefinitionId",
        description="ID of the generic object definition used when creating new objects from this tab.",
    )
    table_view: Optional[bool] = Field(
        None,
        alias="tableView",
        description="When True, objects in this tab are displayed in a table view instead of the default card view.",
    )
    table_view_widget_groups: Optional[List[str]] = Field(
        None,
        alias="tableViewWidgetGroups",
        description="List of widget group names to display in the table view.",
    )
    table_view_columns: Optional[List[str]] = Field(
        None,
        alias="tableViewColumns",
        description="List of field names to display as columns in the table view.",
    )
    dashboard: Optional[Any] = Field(
        None,
        description="Dashboard configuration for this tab. Defines widgets and layout for the tab's dashboard view.",
    )


class View(BaseStrictModel):
    icon: Optional[str] = Field(
        None,
        description="Icon name or path for this view shown in the navigation menu.",
    )
    name: Optional[str] = Field(
        None,
        description="Internal name of the view used for routing and references.",
    )
    title: Optional[str] = Field(
        None,
        description="Display title of the view shown in the UI.",
    )
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the view within this module.",
    )
    tabs: Optional[List[Tab]] = Field(
        None,
        description="List of tabs within this view. Each tab displays a different subset of generic objects.",
    )


class _StrictGenericModule(BaseStrictModel):
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the generic module. Used to reference this module from generic definitions and types.",
    )
    version: int = Field(
        ...,
        description="Schema version of this module. Used for conflict detection. Typically -1 for new items.",
    )
    locked: Optional[bool] = Field(
        None,
        description="When True, this module is locked and cannot be modified by users.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-defined generic module that cannot be deleted.",
    )
    name: str = Field(
        ...,
        description="Display name of the generic module shown in the navigation menu.",
    )
    from_version: Optional[str] = Field(
        None,
        alias="fromVersion",
        description="Minimum platform version required to use this generic module (e.g. '6.5.0').",
    )
    definition_ids: List[str] = Field(
        None,
        alias="definitionIds",
        description="List of generic object definition IDs that this module manages. Each definition represents a type of object displayed in the module.",
    )
    views: List[View] = Field(
        ...,
        description="List of views in this module. Each view provides a different perspective on the module's generic objects.",
    )


StrictGenericModule = create_model(
    model_name="StrictGenericModule",
    base_models=(
        _StrictGenericModule,
        NAME_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
