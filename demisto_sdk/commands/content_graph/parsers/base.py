from abc import ABC, abstractmethod
from typing import Any, Dict

from demisto_sdk.commands.content_graph.constants import ContentTypes


class BaseContentParser(ABC):
    """ An abstract class for all content types.

    Attributes:
        content_type (ContentTypes): The content type.
        node_id      (str):          A unique ID representing the parsed content node.
                                         Should be in the format `<content_type>:<content_id>`.
        deprecated   (bool):         Whether the content is deprecated or not.
    
    Methods:
        get_data (Dict[str, Any]): Returns the data of the parsed content.
    """
    @property
    @abstractmethod
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

    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """ Returns the data of the parsed content. """
        pass
