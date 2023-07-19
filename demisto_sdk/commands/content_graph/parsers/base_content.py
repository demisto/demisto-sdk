from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.content_graph.common import ContentType


class BaseContentParser(ABC):
    """An abstract class for all content types.

    Attributes:
        object_id (str): The content object ID.
        content_type (ContentType): The content object type.
        node_id (str): The content object node ID.
    """

    content_type: ContentType

    def __init__(self, path: Path) -> None:
        self.path: Path = path

    @property
    @abstractmethod
    def object_id(self) -> Optional[str]:
        pass

    @property
    def node_id(self) -> str:
        return f"{self.content_type}:{self.object_id}"
