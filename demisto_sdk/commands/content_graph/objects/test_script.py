from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_script import (
    BaseScript,
)


class TestScript(BaseScript, content_type=ContentType.TEST_SCRIPT):  # type: ignore[call-arg]
    """Class to differ from script"""
