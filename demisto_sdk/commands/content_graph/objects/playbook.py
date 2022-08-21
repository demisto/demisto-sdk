from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Playbook(ContentItem):
    description: str
    is_test: bool
