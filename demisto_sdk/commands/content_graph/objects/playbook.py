from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_playbook import BasePlaybook


class Playbook(BasePlaybook, content_type=ContentType.TEST_PLAYBOOK):  # type: ignore[call-arg]
    is_test: bool = False
