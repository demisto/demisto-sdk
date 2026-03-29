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
    engine: Optional[str] = Field(
        None,
        description="Name of the execution engine to use for this script (e.g. 'Agent'). Used for specialized execution environments.",
    )


class PromptConfig(BaseStrictModel):
    """Configuration for LLM prompt settings."""

    temperature: Optional[float] = Field(
        None,
        description="LLM temperature parameter controlling randomness (0.0-1.0). Lower values produce more deterministic outputs.",
    )
    max_output_tokens: Optional[int] = Field(
        None,
        alias="maxOutputTokens",
        description="Maximum number of tokens the LLM can generate in a single response.",
    )
    web_search: Optional[bool] = Field(
        None,
        alias="webSearch",
        description="When True, the LLM can perform web searches to augment its responses.",
    )


class ContentItemFields(BaseStrictModel):
    from_server_version: Optional[str] = Field(
        None,
        alias="fromServerVersion",
        description="Minimum server version required for this content item's exportable fields.",
    )


class ContentItemExportableFields(BaseStrictModel):
    content_item_fields: Optional[ContentItemFields] = Field(
        None,
        alias="contentitemfields",
        description="Exportable content item fields configuration.",
    )


class _StrictScript(BaseIntegrationScript):  # type:ignore[misc,valid-type]
    common_fields: CommonFieldsScript = Field(
        ...,
        alias="commonfields",
        description="Common metadata fields including the script's unique ID and schema version.",
    )
    name_x2: Optional[str] = Field(
        None,
        description="Alternative name for the script in the X2 marketplace.",
    )
    script: Optional[str] = Field(
        None,
        description="The script source code. For Python scripts, this is the Python source. For unified scripts, this is '-'.",
    )
    type_: ScriptType = Field(
        ...,
        alias="type",
        description="Script language type. Must be one of: 'python3', 'python2', 'powershell', 'javascript'.",
    )
    tags: Optional[List[str]] = Field(
        None,
        description="List of tags for categorizing and filtering this script in the marketplace.",
    )
    enabled: Optional[bool] = Field(
        None,
        description="When True, this script is enabled and can be executed. When False, the script is disabled.",
    )
    args: Optional[List[Argument]] = Field(  # type:ignore[valid-type]
        None,
        description="List of input arguments accepted by this script.",
    )
    script_target: Optional[int] = Field(
        None,
        alias="scripttarget",
        description="Target environment for script execution. 0=XSOAR server, 1=Remote agent.",
    )
    timeout: Optional[str] = Field(
        None,
        description="Script execution timeout (e.g. '5m', '1h'). Script is terminated if it exceeds this duration.",
    )
    depends_on: dict = Field(
        {},
        alias="dependson",
        description="Dictionary of commands this script depends on. Used for dependency resolution during pack installation.",
    )
    outputs: Optional[List[Output]] = Field(
        None,
        description="List of output fields returned by this script. Defines the context paths populated after execution.",
    )
    important: Optional[List[Important]] = Field(  # type:ignore[valid-type]
        None,
        description="List of important outputs to highlight in the UI. These outputs are shown prominently in the war room.",
    )
    docker_image: str = Field(
        None,
        alias="dockerimage",
        description="Docker image used to run this script (e.g. 'demisto/python3:3.10.12.63474'). Must be a valid Docker image tag.",
    )
    docker_image_45: str = Field(
        None,
        alias="dockerimage45",
        description="Docker image for XSOAR 4.5 compatibility. Used for backward compatibility with older platform versions.",
    )
    alt_docker_images: Optional[List[str]] = Field(
        None,
        alias="alt_dockerimages",
        description="Alternative Docker images for different platforms. Used for multi-architecture support.",
    )
    native_image: Optional[List[str]] = Field(
        None,
        alias="nativeImage",
        description="Native image configurations for running without Docker. Used for native execution environments.",
    )
    runonce: Optional[bool] = Field(
        None,
        description="When True, this script runs only once and then stops. Used for one-time setup scripts.",
    )
    sensitive: Optional[bool] = Field(
        None,
        description="When True, the script's output is treated as sensitive and masked in logs.",
    )
    run_as: Optional[str] = Field(
        None,
        alias="runas",
        description="User context to run the script as (e.g. 'DBotWeakRole'). Controls script permissions.",
    )
    sub_type: Optional[ScriptSubType] = Field(
        None,
        alias="subtype",
        description="Python sub-type. Must be 'python3' or 'python2'. Determines which Python version is used.",
    )
    engine_info: Optional[EngineInfo] = Field(
        None,
        alias="engineinfo",
        description="Engine configuration for specialized execution environments.",
    )
    content_item_exportable_fields: Optional[ContentItemExportableFields] = Field(
        None,
        alias="contentitemexportablefields",
        description="Exportable fields configuration for content item export.",
    )
    polling: Optional[bool] = Field(
        None,
        description="When True, this script supports polling mode for long-running operations.",
    )
    skip_prepare: Optional[List[SkipPrepare]] = Field(
        None,
        alias="skipprepare",
        description="List of prepare steps to skip during content preparation. Currently only supports 'script-name'.",
    )
    prettyname: Optional[str] = Field(
        None,
        description="Human-readable display name of the script shown in the UI.",
    )
    compliantpolicies: Optional[List[str]] = Field(
        None,
        alias="compliantpolicies",
        description="List of compliance policy names this script satisfies. Used for compliance reporting.",
    )
    is_llm: bool = Field(
        False,
        alias="isllm",
        description="When True, this script is an LLM-based script. Requires userprompt and either model (legacy) or promptConfig (new format). Mutually exclusive with script code.",
    )
    is_internal: bool = Field(
        False,
        alias="isInternal",
        description="When True, marks this script as internal and not intended for direct use by end users.",
    )
    internal: bool = Field(
        False,
        alias="internal",
        description="When True, marks this script as internal.",
    )
    source: Optional[str] = Field(
        None,
        description="Source repository or origin of this script.",
    )
    model: Optional[str] = Field(
        None,
        description="LLM model name for legacy LLM scripts (toversion: 8.12.0). Required when isllm=True in legacy format.",
    )
    user_prompt: Optional[str] = Field(
        None,
        alias="userprompt",
        description="User-facing prompt template for LLM scripts. Required when isllm=True. Defines the task the LLM performs.",
    )
    system_prompt: Optional[str] = Field(
        None,
        alias="systemprompt",
        description="System-level instructions for the LLM. Defines the LLM's persona and behavior constraints.",
    )
    few_shots: Optional[str] = Field(
        None,
        alias="fewshots",
        description="Few-shot examples for the LLM. Provides example inputs and outputs to guide the LLM's responses.",
    )
    prompt_config: Optional[PromptConfig] = Field(
        None,
        alias="promptConfig",
        description="LLM prompt configuration for new-format LLM scripts (fromversion: 8.13.0). Mutually exclusive with legacy model field.",
    )

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
