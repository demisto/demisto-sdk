from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook


class TestPlaybook(Playbook, content_type=ContentType.TEST_PLAYBOOK):
    pass

    def included_in_metadata(self) -> Set[str]:
        raise NotImplementedError('TestPlaybooks not included in metadata')
