from typing import List, Optional

from pydantic import Field, root_validator

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


class PromptConfig(BaseStrictModel):
    """Configuration for LLM prompt settings."""

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    web_search: Optional[bool] = Field(None, alias="webSearch")


class ContentItemFields(BaseStrictModel):
    from_server_version: Optional[str] = Field(None, alias="fromServerVersion")


class ContentItemExportableFields(BaseStrictModel):
    content_item_fields: Optional[ContentItemFields] = Field(
        None, alias="contentitemfields"
    )


class _StrictScript(BaseIntegrationScript):  # type:ignore[misc,valid-type]
    common_fields: CommonFieldsScript = Field(..., alias="commonfields")
    name_x2: Optional[str] = None
    script: Optional[str] = None
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
    compliantpolicies: Optional[List[str]] = Field(None, alias="compliantpolicies")
    is_llm: bool = Field(False, alias="isllm")
    is_internal: bool = Field(False, alias="isInternal")
    internal: bool = Field(False, alias="internal")
    source: Optional[str] = None
    model: Optional[str] = None
    user_prompt: Optional[str] = Field(None, alias="userprompt")
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")
    prompt_config: Optional[PromptConfig] = Field(None, alias="promptConfig")

    @root_validator
    def validate_llm_constraints(cls, values):
        """
        Validates LLM-related field constraints based on the 'is_llm' flag.

        Supports two formats:
        1. Legacy format: Uses 'model' field at root level
        2. New format: Uses 'promptConfig' object

        - If 'is_llm' is True:
            - 'script' must be empty.
            - 'user_prompt' must be provided.
            - Either 'model' (legacy) or 'promptConfig' (new) should be used.
            - If using new format without 'model', promptConfig defaults apply.

        - If 'is_llm' is False:
            - All LLM-related fields must be None or empty.

        Raises:
            ValueError: If one or more validation conditions are not met.
        """
        errors = []
        if values.get("is_llm"):
            # Enforce LLM mode rules
            if values.get("script"):
                errors.append(
                    "When 'isllm' is True, 'script' should not appear in yml."
                )
            if not values.get("model") and not values.get("prompt_config"):
                errors.append(
                    "When 'isllm' is True, either 'model' (legacy format with toversion: 8.12.0) "
                    "or 'promptConfig' (new format with fromversion: 8.13.0) must be provided."
                )
            if not values.get("user_prompt"):
                errors.append("When 'isllm' is True, 'userprompt' must be provided.")
        else:
            # Enforce non-LLM mode: all LLM-related fields must be None or empty
            llm_fields = [
                ("model", values.get("model")),
                ("user_prompt", values.get("user_prompt")),
                ("system_prompt", values.get("system_prompt")),
                ("few_shots", values.get("few_shots")),
                ("prompt_config", values.get("prompt_config")),
            ]
            errors.extend(
                f"Field '{field_name}' must be empty when 'isllm' is False."
                for field_name, value in llm_fields
                if value not in [None, ""]
            )
        if errors:
            raise ValueError("Validation failed:\n" + "\n".join(errors))

        return values


StrictScript = create_model(
    model_name="StrictScript",
    base_models=(
        _StrictScript,
        COMMENT_DYNAMIC_MODEL,
    ),
)
