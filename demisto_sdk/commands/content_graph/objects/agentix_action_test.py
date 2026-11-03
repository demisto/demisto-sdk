from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import AGENTIX_ACTIONS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase


class AgentixActionTestCase(BaseModel):
    prompt: str
    agent_id: str
    expected_outcomes: Optional[List[dict]] = None


class AgentixActionTest(AgentixBase, content_type=ContentType.AGENTIX_ACTION_TEST):
    description: str = ""
    display_name: str = ""
    tests: List[AgentixActionTestCase] = Field([], exclude=True)

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if AGENTIX_ACTIONS_DIR in path.parts and path.suffix in (".yml", ".yaml"):
            # New pattern: <action_id>_test.yml
            if path.stem.endswith("_test"):
                return True
            # Old pattern: test_<action_id>.yaml (in test_data directory)
            if path.stem.startswith("test_") and "test_data" in path.parts:
                return True
        return False
