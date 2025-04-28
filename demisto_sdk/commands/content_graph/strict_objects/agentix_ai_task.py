from typing import Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript


class AgentixAITask(StrictScript):
    is_llm: bool = Field(..., alias="isLLM")
    pre_script: str = Field('', alias="preScript")
    post_script: str = Field('', alias="postScript")
    prompt: str = ''
    few_shots: str = Field('', alias="fewShots")
