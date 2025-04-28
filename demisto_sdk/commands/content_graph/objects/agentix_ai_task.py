from pathlib import Path

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)


class AgentixAITask(IntegrationScript):
    is_llm: bool = Field(..., alias="isLLM")
    pre_script: str = Field('', alias="preScript")
    post_script: str = Field('', alias="postScript")
    prompt: str = ''
    few_shots: str = Field('', alias="fewShots")


    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass