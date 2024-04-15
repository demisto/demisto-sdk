from abc import abstractmethod
from pathlib import Path

from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class TestSuiteBase:
    def __init__(self, path: Path):
        self.obj_path = path

    @property
    def object(self):
        obj = BaseContent.from_path(self.obj_path)
        assert obj, f"Object not found in path: {self.obj_path}"
        return obj

    def get_graph_object(self, interface: ContentGraphInterface):
        """Returns content item from the graph, enriched with the relationships.

        Args:
            interface (ContentGraphInterface): The ContentGraphInterface instance to work with.

        Returns:
            Union[Pack, ContentItem]: The content item found
        """
        return interface.from_path(self.obj_path)

    @abstractmethod
    def set_data(self, key_path_to_val: dict):
        """Should be implemented by the sub classes to update the existing content.

        Args:
            key_path_to_val (dict): a dict with 'path to be updated': 'value'.
            for example: 'script.dockerimage': 'new_image
        """
        pass

    def clear_from_path_cache(self):
        """Rest the BaseContent `from_path` lru_cache."""
        BaseContent.from_path.cache_clear()
