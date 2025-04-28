from pydantic import Field

from demisto_sdk.commands.content_graph.objects import BaseScript


class AgentixAITask(BaseScript):
    is_llm: bool = Field(..., alias="isLLM")
    pre_script: str = Field('', alias="preScript")
    post_script: str = Field('', alias="postScript")
    prompt: str = ''
    few_shots: str = Field('', alias="fewShots")
