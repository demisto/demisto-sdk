from abc import abstractmethod
from pathlib import Path

from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class TestSuiteBase:
    def __init__(self, path: Path):
        self.obj_path = path
        
    
    @property
    def object(self):
        return BaseContent.from_path(self.obj_path)

    def get_graph_object(self, interface: ContentGraphInterface):
        return interface.from_path(self.obj_path)
    
    @abstractmethod
    def set_data(key_path_to_val: dict):
        """Should be implemented by the sub classes to update the existing content.

        Args:
            key_path_to_val (dict): a dict with 'path to be updated': 'value'.
            for example: 'script.dockerimage': 'new_image
        """
        pass
    
    def clear_from_path_cache(self):
        """Rest the BaseContent `from_path` lru_cache.
        """
        BaseContent.from_path.cache_clear()

    
