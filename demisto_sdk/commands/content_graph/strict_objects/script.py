from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    TYPE_PYTHON2,
    TYPE_PYTHON3,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    Argument,
    BaseIntegrationScript,
    CommonFields,
    Important,
    Output,
    ScriptType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
    create_dynamic_model,
    create_model,
)

COMMENT_DYNAMIC_MODEL = create_dynamic_model(
    field_name="comment",
    type_=Optional[str],
    default=None,
    suffixes=[MarketplaceVersions.MarketplaceV2.value],
    include_without_suffix=True,
)


class SkipPrepare(StrEnum):
    SCRIPT_NAME = SKIP_PREPARE_SCRIPT_NAME


class ScriptSubType(StrEnum):
    PYTHON3 = TYPE_PYTHON3
    PYTHON2 = TYPE_PYTHON2


class CommonFieldsScript(CommonFields):  # type:ignore[misc,valid-type]
    id_x2: Optional[str] = None
    id_xpanse: Optional[str] = Field(None, alias="id:xpanse")


class EngineInfo(BaseStrictModel):
    engine: Optional[str] = None


class ContentItemFields(BaseStrictModel):
    from_server_version: Optional[str] = Field(None, alias="fromServerVersion")


class ContentItemExportableFields(BaseStrictModel):
    content_item_fields: Optional[ContentItemFields] = Field(
        None, alias="contentitemfields"
    )


class _StrictScript(BaseIntegrationScript):  # type:ignore[misc,valid-type]
    common_fields: CommonFieldsScript = Field(..., alias="commonfields")
    name_x2: Optional[str] = None
    script: str
    type_: ScriptType = Field(..., alias="type")
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None
    args: Optional[List[Argument]] = None  # type:ignore[valid-type]
    script_target: Optional[int] = Field(None, alias="scripttarget")
    timeout: Optional[str] = None
    depends_on: dict = Field({}, alias="dependson")
    outputs: Optional[List[Output]] = None
    important: Optional[List[Important]] = None  # type:ignore[valid-type]
    docker_image: str = Field(None, alias="dockerimage")
    docker_image_45: str = Field(None, alias="dockerimage45")
    alt_docker_images: Optional[List[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[List[str]] = Field(None, alias="nativeImage")
    runonce: Optional[bool] = None
    sensitive: Optional[bool] = None
    run_as: Optional[str] = Field(None, alias="runas")
    sub_type: Optional[ScriptSubType] = Field(None, alias="subtype")
    engine_info: Optional[EngineInfo] = Field(None, alias="engineinfo")
    content_item_exportable_fields: Optional[ContentItemExportableFields] = Field(
        None, alias="contentitemexportablefields"
    )
    polling: Optional[bool] = None
    skip_prepare: Optional[List[SkipPrepare]] = Field(None, alias="skipprepare")
    prettyname: Optional[str] = None


StrictScript = create_model(
    model_name="StrictScript",
    base_models=(
        _StrictScript,
        COMMENT_DYNAMIC_MODEL,
    ),
)
