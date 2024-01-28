from pathlib import Path
from typing import List

from pydantic import Field

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_script import Argument, BaseScript


class TestScriptArgument(Argument):
    description: str = (
        ""  # TestScripts can have missing descriptions in their arguments
    )


class TestScript(BaseScript, content_type=ContentType.TEST_SCRIPT):  # type: ignore[call-arg]
    """Class to differ from script"""

    args: List[TestScriptArgument] = Field([], exclude=True)  # type: ignore[assignment]

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "script" in _dict:
            if TEST_PLAYBOOKS_DIR in path.parts and path.suffix == ".yml":
                return True
        return False
