from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class List(ContentItem):
    type: str

    def summary(self):
        return self.dict(include=['name'])
