from pathlib import Path
from typing import Set

from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_playbook import BasePlaybook


class TestPlaybook(BasePlaybook, content_type=ContentType.TEST_PLAYBOOK):  # type: ignore[call-arg]
    is_test: bool = True

    def metadata_fields(self) -> Set[str]:
        raise NotImplementedError("TestPlaybooks not included in metadata")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            TEST_PLAYBOOKS_DIR in path.parts
            and "tasks" in _dict
            and path.suffix == ".yml"
        ):
            return True
        return False
