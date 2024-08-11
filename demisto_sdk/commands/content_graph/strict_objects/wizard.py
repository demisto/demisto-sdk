from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEPRECATED_DYNAMIC_MODEL,
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class Action(BaseStrictModel):
    existing: Optional[str] = None
    new: Optional[str] = None


class _Integrations(BaseStrictModel):
    name: str
    description: str
    action: Action
    priority: Optional[int] = None
    incident_type: Optional[str] = None


Integrations = create_model(
    model_name="Integrations",
    base_models=(
        _Integrations,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)


class _Playbook(BaseStrictModel):
    name: str
    link_to_integration: Optional[str] = None


Playbook = create_model(
    model_name="Playbook",
    base_models=(
        _Playbook,
        NAME_DYNAMIC_MODEL,
    ),
)


class _NextWizard(BaseStrictModel):
    name: str
    action: Action


NextWizard = create_model(
    model_name="NextWizard", base_models=(_NextWizard, NAME_DYNAMIC_MODEL)
)


class Pack(BaseStrictModel):
    name: Optional[str] = None
    display_name: Optional[str] = None


class DependencyPack(BaseStrictModel):
    name: str
    min_required: int
    packs: Optional[List[Pack]] = None


class Wizard(BaseStrictModel):
    fetching_integrations: List[Integrations]  # type:ignore[valid-type]
    supporting_integrations: List[Integrations]  # type:ignore[valid-type]
    set_playbook: List[Playbook]  # type:ignore[valid-type]
    next: Optional[List[NextWizard]] = None  # type:ignore[valid-type]


class _StrictWizard(BaseStrictModel):
    id_: str = Field(alias="id")
    version: Optional[int] = None
    name: str
    modified: Optional[str] = None
    description: Optional[str] = None
    system: Optional[bool] = None
    deprecated: Optional[bool] = None
    from_version: str = Field(alias="fromVersion")
    to_version: Optional[str] = Field(None, alias="toVersion")
    dependency_packs: List[DependencyPack]
    wizard: Wizard


StrictWizard = create_model(
    model_name="StrictWizard",
    base_models=(
        _StrictWizard,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
