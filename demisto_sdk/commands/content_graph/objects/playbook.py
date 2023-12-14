from pathlib import Path

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_playbook import BasePlaybook


class Playbook(BasePlaybook, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    is_test: bool = False

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "tasks" in _dict:
            if TEST_PLAYBOOKS_DIR not in path.parts and path.suffix == ".yml":
                return True
        return False
