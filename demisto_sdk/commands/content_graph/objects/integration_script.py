from abc import abstractmethod
from pathlib import Path
from typing import List

from pydantic import Field

from demisto_sdk.commands.content_graph.objects.content_item import YAMLContentItem
from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier


class IntegrationScript(YAMLContentItem):
    type: str = ''
    docker_image: str = ''
    is_unified: bool = False
    unifier: IntegrationScriptUnifier = None

    def __post_init__(self) -> None:
        if self.should_parse_object:
            self.object_id = self.yml_data.get('commonfields', {}).get('id')
            self.is_unified = YAMLContentItem.is_unified_file(self.path)
            self.unifier = None if self.is_unified else IntegrationScriptUnifier(self.path.as_posix())

    @abstractmethod
    def get_code(self) -> str:
        pass
