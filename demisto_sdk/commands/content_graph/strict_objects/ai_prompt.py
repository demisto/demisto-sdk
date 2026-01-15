from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionYaml,
    CommonFields,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEPRECATED_DYNAMIC_MODEL,
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class PromptConfig(BaseStrictModel):
    """Configuration for LLM prompt settings."""

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    web_search: Optional[bool] = Field(None, alias="webSearch")


class AIPromptArgument(BaseStrictModel):
    """Argument definition for AIPrompt."""

    name: str
    description: str
    required: bool = False
    default: Optional[str] = None


class _AIPrompt(BaseStrictModel):
    """Strict validation model for AIPrompt content items.

    This model enforces the required structure for AIPrompt YAML files.
    The userprompt field is mandatory - it contains the main LLM prompt text.
    """

    common_fields: CommonFields = Field(..., alias="commonfields")  # type: ignore[valid-type]
    name: str
    type_: str = Field("aiprompt", alias="type")
    description: str
    user_prompt: str = Field(..., alias="userprompt")  # Required field
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")
    model: Optional[str] = None
    pre_script: Optional[str] = Field(None, alias="prescript")
    post_script: Optional[str] = Field(None, alias="postscript")
    prompt_config: Optional[PromptConfig] = Field(None, alias="promptConfig")
    arguments: Optional[list[AIPromptArgument]] = None
    password: Optional[str] = None
    private: bool = False
    tags: Optional[list[str]] = None
    deprecated: Optional[bool] = None


AIPrompt = create_model(
    model_name="AIPrompt",
    base_models=(
        _AIPrompt,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        DEPRECATED_DYNAMIC_MODEL,
        BaseOptionalVersionYaml,
    ),
)
