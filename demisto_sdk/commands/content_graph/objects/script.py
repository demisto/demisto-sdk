from typing import List

from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class Script(IntegrationScript):
    tags: List[str]
    is_test: bool
    
    def summary(self):
        return self.dict(include=['name', 'description', 'tags'])
