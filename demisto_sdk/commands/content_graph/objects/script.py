from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_script import (
    BaseScript,
)


class PromptConfig(BaseModel):
    """Configuration for LLM prompt settings."""

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = Field(None, alias="maxOutputTokens")
    web_search: Optional[bool] = Field(None, alias="webSearch")


class Script(BaseScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    """Class to differ from test script"""

    is_llm: bool = Field(False, alias="isllm")
    is_internal: bool = Field(False, alias="isInternal")
    internal: bool = Field(False, alias="internal")
    source: str = Field("")
    model: Optional[str] = None
    user_prompt: Optional[str] = Field(None, alias="userprompt")
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")
    prompt_config: Optional[PromptConfig] = Field(
        None, alias="promptConfig", exclude=True
    )

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            ("script" in _dict and isinstance(_dict["script"], str)) or "isllm" in _dict
        ) and path.suffix == ".yml":
            if TEST_PLAYBOOKS_DIR not in path.parts:
                return True
        return False
