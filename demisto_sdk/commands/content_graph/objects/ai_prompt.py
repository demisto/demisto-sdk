from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class PromptConfig(BaseModel):
    """Configuration for LLM prompt settings."""

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    web_search: Optional[bool] = Field(None, alias="webSearch")


class AIPromptArgument(BaseModel):
    """Argument definition for AIPrompt."""

    name: str
    description: str
    required: bool = False
    default: Optional[str] = None


class AIPrompt(ContentItem, content_type=ContentType.AIPROMPT):  # type: ignore[call-arg]
    """AIPrompt content item - represents an LLM prompt configuration.

    AIPrompts are configuration files that define how to interact with LLMs.
    They contain the prompt text, pre/post processing scripts, and LLM settings.
    Unlike Scripts with isllm=true, AIPrompts are dedicated content items.
    """

    user_prompt: str = Field(..., alias="userprompt")
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")
    model: Optional[str] = None
    pre_script: Optional[str] = Field(None, alias="prescript")
    post_script: Optional[str] = Field(None, alias="postscript")
    prompt_config: Optional[PromptConfig] = Field(
        None, alias="promptConfig", exclude=True
    )
    arguments: Optional[list[AIPromptArgument]] = Field(None, exclude=True)
    password: Optional[str] = Field(None, exclude=True)
    private: bool = False
    source_script_id: Optional[str] = Field(None, alias="sourcescripid")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Check if the file is an AIPrompt by looking for type: aiprompt."""
        if path.suffix == ".yml" and _dict.get("type") == "aiprompt":
            return True
        return False

    def metadata_fields(self) -> set:
        """Return the metadata fields for AIPrompt summary."""
        fields = super().metadata_fields()
        fields.update(
            {
                "model",
                "private",
            }
        )
        return fields
