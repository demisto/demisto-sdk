from abc import abstractmethod
from typing import Iterator, List, Union

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import \
    ClassifierObject
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import \
    LayoutObject


class BaseConverter:
    def __init__(self):
        pass

    @abstractmethod
    def convert_dir(self):
        pass

    @staticmethod
    def get_entities_by_entity_type(entities: Union[Iterator[LayoutObject], Iterator[ClassifierObject]],
                                    entity_type: FileType) -> Union[List[LayoutObject], List[ClassifierObject]]:
        """
        Returns all entities in the given pack whom entity type matches the 'entity_type' argument given.
        Args:
            entities (Union[Iterator[LayoutObject], Iterator[ClassifierObject]]): Entities.
            entity_type (FileType): The entity type.

        Returns:
            (Union[List[LayoutObject], List[ClassifierObject]]): List of entities whom type matches 'entity_type'.
        """
        return [entity for entity in entities if entity.type() == entity_type]
