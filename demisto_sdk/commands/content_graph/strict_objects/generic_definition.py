from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictGenericDefinition(BaseStrictModel):
    id_: str = Field(
        ...,
        alias="id",
        description="Unique identifier of the generic object definition. Used to reference this definition from generic fields, modules, and types.",
    )
    name: str = Field(
        ...,
        description="Display name of the generic object definition shown in the UI.",
    )
    partitioned: Optional[bool] = Field(
        None,
        description="When True, generic objects of this type are partitioned per tenant in multi-tenant environments.",
    )
    auditable: bool = Field(
        ...,
        description="When True, changes to generic objects of this type are tracked in the audit log.",
    )
    rbac_support: Optional[bool] = Field(
        None,
        alias="rbacSupport",
        description="When True, Role-Based Access Control (RBAC) is enforced for generic objects of this type.",
    )
    version: Optional[int] = Field(
        None,
        description="Schema version of this definition. Used for conflict detection. Typically -1 for new items.",
    )
    locked: Optional[bool] = Field(
        None,
        description="When True, this definition is locked and cannot be modified by users.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-defined generic object definition that cannot be deleted.",
    )
    from_version: str = Field(
        ...,
        alias="fromVersion",
        description="Minimum platform version required to use this generic object definition (e.g. '6.5.0'). Required field.",
    )
    plural_name: Optional[str] = Field(
        None,
        alias="pluralName",
        description="Plural form of the object name used in the UI (e.g. 'Assets', 'Vulnerabilities').",
    )


StrictGenericDefinition = create_model(
    model_name="StrictGenericDefinition",
    base_models=(
        _StrictGenericDefinition,
        NAME_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
