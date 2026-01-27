from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import AGENTIX_ACTIONS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixTestCase(BaseModel):
    prompt: str
    agent_id: str
    expected_outcomes: Optional[List[dict]] = None


class AgentixTest(AgentixBase, content_type=ContentType.AGENTIX_TEST):
    description: str = ""
    display_name: str = ""
    tests: List[AgentixTestCase] = Field([], exclude=True)

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            AGENTIX_ACTIONS_DIR in path.parts
            and path.suffix == ".yml"
            and path.stem.endswith("_test")
        ):
            return True
        return False
