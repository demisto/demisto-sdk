from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook


class TestPlaybook(Playbook, content_type=ContentType.TEST_PLAYBOOK):  # type: ignore[call-arg]
    is_test: bool = True
