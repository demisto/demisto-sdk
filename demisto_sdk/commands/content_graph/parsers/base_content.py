from abc import ABC, abstractmethod
from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContentParser(ABC):
    """ An abstract class for all content types.

    Attributes:
        object_id    (str):          The content object ID.
        content_type (ContentTypes): The content object type.
        node_id      (str):          The content object node ID.
    """
    
    def __init__(self, path: Path) -> None:
        self.path = path

    @abstractmethod
    @property
    def object_id(self) -> str:
        pass

    @property
    @abstractmethod
    def content_type(self) -> ContentTypes:
        pass

    @property
    def node_id(self) -> str:
        return f'{self.content_type}:{self.object_id}'
