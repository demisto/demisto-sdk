from pydantic import Field
from typing import Optional

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel, create_model, NAME_DYNAMIC_MODEL


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

    id_xsoar: Optional[str] = Field(None, alias='id:xsoar')
    id_marketplacev2: Optional[str] = Field(None, alias='id:marketplacev2')
    id_xpanse: Optional[str] = Field(None, alias='id:xpanse')
    id_xsoar_saas: Optional[str] = Field(None, alias='id:xsoar_saas')
    id_xsoar_on_prem: Optional[str] = Field(None, alias='id:xsoar_on_prem')


StrictGenericDefinition = create_model(model_name="StrictGenericDefinition",
                                       base_models=(_StrictGenericDefinition,
                                                    NAME_DYNAMIC_MODEL,
                                                    ))