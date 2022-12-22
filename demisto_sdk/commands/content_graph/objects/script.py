from typing import List, Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class Script(IntegrationScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    tags: List[str]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description", "tags"}
