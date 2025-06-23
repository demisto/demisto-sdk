from pathlib import Path
from typing import Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_script import (
    BaseScript,
)


class Script(BaseScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    """Class to differ from test script"""

    is_llm: bool = Field(False, alias="isllm")
    model: Optional[str] = None
    user_prompt: Optional[str] = Field(None, alias="userprompt")
    system_prompt: Optional[str] = Field(None, alias="systemprompt")
    few_shots: Optional[str] = Field(None, alias="fewshots")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            ("script" in _dict and isinstance(_dict["script"], str)) or "isllm" in _dict
        ) and path.suffix == ".yml":
            if TEST_PLAYBOOKS_DIR not in path.parts:
                return True
        return False
