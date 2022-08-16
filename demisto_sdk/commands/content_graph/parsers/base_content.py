from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContentParser(ABC):
    """ An abstract class for all content types.

    Attributes:
        object_id    (str):          The content object ID.
        node_id      (str):          The content object node ID.
        content_type (ContentTypes): The content type.
        deprecated   (bool):         Whether the content is deprecated or not.
        marketplaces (List[str]):    The marketplaces in which the content should be.

    """
    
    def __init__(self, path: Path) -> None:
        self.path = path
        
    @abstractmethod
    @property
    def object_id(self) -> str:
        pass

    @abstractmethod
    @property
    def node_id(self) -> str:
        pass

    @property
    @abstractmethod
    def content_type(self) -> ContentTypes:
        pass

    @property
    @abstractmethod
    def deprecated(self) -> bool:
        pass

    @property
    @abstractmethod
    def marketplaces(self) -> List[str]:
        pass
