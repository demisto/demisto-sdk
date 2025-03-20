from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictIndicatorType(BaseStrictModel):
    modified: Optional[str] = None
    id_: str = Field(alias="id")
    version: int
    sort_values: Optional[Any] = Field(None, alias="sortValues")
    commit_message: Optional[str] = Field(None, alias="commitMessage")
    should_publish: Optional[bool] = Field(None, alias="shouldPublish")
    should_commit: Optional[bool] = Field(None, alias="shouldCommit")
    regex: str
    details: str
    prev_details: Optional[str] = Field(None, alias="prevDetails")
    reputation_script_name: Optional[str] = Field(None, alias="reputationScriptName")
    reputation_command: Optional[str] = Field(None, alias="reputationCommand")
    enhancement_script_names: Optional[Any] = Field(
        None, alias="enhancementScriptNames"
    )
    system: Optional[bool] = None
    locked: Optional[bool] = None
    disabled: Optional[bool] = None
    file: Optional[bool] = None
    update_after: Optional[int] = Field(None, alias="updateAfter")
    merge_context: Optional[bool] = Field(None, alias="mergeContext")
    format_script: Optional[str] = Field(None, alias="formatScript")
    context_path: Optional[str] = Field(None, alias="contextPath")
    context_value: Optional[str] = Field(None, alias="contextValue")
    excluded_brands: Optional[Any] = Field(None, alias="excludedBrands")
    default_mapping: Optional[Any] = Field(None, alias="defaultMapping")
    manual_mapping: Optional[Any] = Field(None, alias="manualMapping")
    file_hashes_priority: Optional[Any] = Field(None, alias="fileHashesPriority")
    expiration: Optional[int] = None
    layout: Optional[str] = None
    legacy_names: Optional[List[str]] = Field(None, alias="legacyNames")
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictIndicatorType = create_model(
    model_name="StrictIndicatorType",
    base_models=(
        _StrictIndicatorType,
        BaseOptionalVersionJson,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)
