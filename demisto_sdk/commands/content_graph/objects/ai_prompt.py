from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration_script import (
    Argument,
    Output,
)


class PromptConfig(BaseModel):
    """Configuration for LLM prompt settings."""

    model: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    system_instruction: Optional[str] = Field(None, alias="systemInstruction")
    web_search: Optional[bool] = Field(None, alias="webSearch")


class AIPrompt(ContentItem, content_type=ContentType.AIPROMPT):  # type: ignore[call-arg]
    """AIPrompt content item - represents an LLM prompt configuration.

    AIPrompts are configuration files that define how to interact with LLMs.
    They contain the prompt text, pre/post processing scripts, and LLM settings.
    Unlike Scripts with isllm=true, AIPrompts are dedicated content items.
    """

    # Core prompt fields
    user_prompt: str = Field(..., alias="userprompt")
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")
    pre_script: Optional[str] = Field(None, alias="prescript")
    post_script: Optional[str] = Field(None, alias="postscript")
    prompt_config: Optional[PromptConfig] = Field(
        None, alias="promptConfig", exclude=True
    )

    # Arguments and outputs
    arguments: Optional[List[Argument]] = Field(None, exclude=True)
    outputs: Optional[List[Output]] = Field(None, exclude=True)

    # Metadata fields from schema
    version: int = -1
    tags: Optional[List[str]] = None
    pretty_name: Optional[str] = Field(None, alias="prettyname")
    comment: Optional[str] = None

    # Boolean flags
    private: bool = False
    is_internal: bool = Field(False, alias="isInternal")
    is_anonymous: bool = Field(False, alias="isanonymous")
    enabled: bool = True
    system: bool = False
    locked: bool = False
    sensitive: bool = False
    hidden: bool = False

    # Execution settings
    run_as: Optional[str] = Field(None, alias="runas")
    timeout: Optional[str] = None
    password: Optional[str] = Field(None, alias="pswd", exclude=True)
    compliant_policies: Optional[List[str]] = Field(
        None, alias="compliantpolicies"
    )

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
                "private",
                "tags",
            }
        )
        return fields
