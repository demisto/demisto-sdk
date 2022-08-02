from abc import ABC, abstractmethod
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes, MARKETPLACE_PROPERTIES


class BaseContentParser(ABC):
    """ An abstract class for all content types.

    Attributes:
        content_type (ContentTypes): The content type.
        deprecated   (bool):         Whether the content is deprecated or not.
        marketplaces (List[str]):    The marketplaces in which the content should be.
    
    Methods:
        get_data (Dict[str, Any]): Returns the data of the parsed content.
    """

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

    def get_data(self) -> Dict[str, Any]:
        base_data: Dict[str, Any] = {
            'deprecated': self.deprecated,
            'marketplaces': self.marketplaces,
        }
        return base_data
