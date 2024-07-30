from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    ID_JUST_WITH_SUFFIX_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictGenericDefinition(BaseStrictModel):
    id_: str = Field(alias="id")
    name: str
    partitioned: Optional[bool] = None
    auditable: bool
    rbac_support: Optional[bool] = Field(None, alias="rbacSupport")
    version: Optional[int] = None
    locked: Optional[bool] = None
    system: Optional[bool] = None
    from_version: str = Field(alias="fromVersion")
    plural_name: Optional[str] = Field(None, alias="pluralName")


StrictGenericDefinition = create_model(
    model_name="StrictGenericDefinition",
    base_models=(
        _StrictGenericDefinition,
        NAME_DYNAMIC_MODEL,
        ID_JUST_WITH_SUFFIX_DYNAMIC_MODEL,
    ),
)
