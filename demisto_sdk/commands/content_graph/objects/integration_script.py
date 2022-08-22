from pathlib import Path
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IntegrationScript(ContentItem):
    type: str
    docker_image: str
    description: str
    code_path: Path
