from pathlib import Path

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_script import (
    BaseScript,
)


class Script(BaseScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    """Class to differ from test script"""

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "script" in _dict
            and isinstance(_dict["script"], str)
            and path.suffix == ".yml"
        ):
            if TEST_PLAYBOOKS_DIR not in path.parts:
                return True
        return False
