
from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.script import _StrictScript


class AgentixAITask(_StrictScript):
    is_llm: bool = Field(..., alias="isLLM")
    pre_script: str = Field('', alias="preScript")
    post_script: str = Field('', alias="postScript")
    user_prompt: str = Field('', alias="userPrompt")
    system_prompt: str = Field('', alias="systemPrompt")
    few_shots: str = Field('', alias="fewShots")
