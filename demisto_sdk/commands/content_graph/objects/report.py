from pathlib import Path

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Report(ContentItem):
    description: str
    json_encoders = {
        Path: lambda v: v.as_posix()
    }
