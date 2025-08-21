from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictList(BaseStrictModel):
    all_read: Optional[bool] = Field(None, alias="allRead")
    all_read_write: Optional[bool] = Field(None, alias="allReadWrite")
    data: Optional[str] = None
    dbot_created_by: Optional[str] = Field(None, alias="dbotCreatedBy")
    description: Optional[str] = Field(None)
    from_version: str = Field(alias="fromVersion")
    has_role: Optional[bool] = Field(None, alias="hasRole")
    id: str
    item_version: str = Field(alias="itemVersion")
    locked: bool
    name: str
    name_locked: bool = Field(alias="nameLocked")
    pack_id: str = Field(alias="packID")
    previous_all_read: Optional[bool] = Field(None, alias="previousAllRead")
    previous_all_write: Optional[bool] = Field(None, alias="previousAllWrite")
    previous_roles: Optional[List[Any]] = Field(None, alias="previousRoles")
    roles: Optional[List[Any]] = None
    system: bool
    tags: Optional[List[str]] = None
    to_version: Optional[str] = Field(None, alias="toVersion")
    truncated: Optional[bool] = None
    type_: str = Field(alias="type")
    version: int
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictList = create_model(
    model_name="StrictList",
    base_models=(
        _StrictList,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
