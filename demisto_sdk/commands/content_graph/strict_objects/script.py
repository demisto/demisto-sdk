from demisto_sdk.commands.common.StrEnum import StrEnum
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import BaseStrictModel, CommonFields, \
    Argument, Output, Important, ScriptType, BaseIntegrationScript
from pydantic import Field


class SkipPrepare(StrEnum):
    SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert"


class ScriptSubType(StrEnum):
    TYPE_PYTHON3 = "python3"
    TYPE_PYTHON2 = "python2"


class ScriptArgument(Argument):
    description_x2: Optional[bool] = None


class CommonFieldsScript(CommonFields):
    id_x2: Optional[str] = None
    id_xpanse: Optional[str] = Field(None, alias="id:xpanse")


class ScriptOutput(Output):
    description: Optional[str] = None
    description_x2: Optional[str] = None


class ScriptImportant(Important):
    description_x2: Optional[str] = None


class EngineInfo(BaseStrictModel):
    engine: Optional[str] = None


class ContentItemFields(BaseStrictModel):
    from_server_version: Optional[str] = Field(None, alias="fromServerVersion")


class ContentItemExportableFields(BaseStrictModel):
    content_item_fields: Optional[ContentItemFields] = Field(None, alias="contentitemfields")


class StrictScript(BaseIntegrationScript):
    common_fields: CommonFieldsScript = Field(..., alias="commonfields")
    name_x2: Optional[str] = None
    script: str
    type_: ScriptType = Field(..., alias="type")
    tags: Optional[list[str]] = None
    comment: Optional[str] = None
    comment_marketplace_v2: Optional[str] = Field(None, alias="comment:marketplacev2")
    enabled: Optional[bool] = None
    args: Optional[list[ScriptArgument]] = None
    script_target: Optional[int] = Field(None, alias="scripttarget")
    timeout: Optional[str] = None
    depends_on: dict = Field({}, alias="dependson")
    depends_on_x2: dict = Field({}, alias="dependson_x2")
    outputs: Optional[list[ScriptOutput]] = None
    important: Optional[list[ScriptImportant]] = None
    docker_image: str = Field(None, alias="dockerimage")
    docker_image_45: str = Field(None, alias="dockerimage45")
    alt_docker_images: Optional[list[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[list[str]] = Field(None, alias="nativeImage")
    runonce: Optional[bool] = None
    sensitive: Optional[bool] = None
    run_as: Optional[str] = Field(None, alias="runas")
    sub_type: Optional[ScriptSubType] = Field(None, alias="subtype")
    engine_info: Optional[EngineInfo] = Field(None, alias="engineinfo")
    content_item_exportable_fields: Optional[ContentItemExportableFields] = \
        Field(None, alias="contentitemexportablefields")
    polling: Optional[bool] = None
    skip_prepare: Optional[list[SkipPrepare]] = Field(None, alias="skipprepare")

# content_packs = Path("/Users/rshunim/dev/demisto/content/Packs/")
# for file in content_packs.rglob("*/Scripts/*/*.yml"):
#     if "DeprecatedContent" in file.parts:
#         continue
#     print(file)
#     script = StrictScript.parse_obj(get_file(file))
