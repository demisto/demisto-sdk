from typing import List
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
from demisto_sdk.commands.content_graph.constants import ContentTypes

class Script(IntegrationScript):
    tags: List[str]