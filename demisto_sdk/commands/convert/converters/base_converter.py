import json
import re
from abc import abstractmethod
from typing import Dict, Iterator, List, Union

from demisto_sdk.commands.common.constants import (ENTITY_NAME_SEPARATORS,
                                                   FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import \
    Classifier
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import \
    LayoutObject


class BaseConverter:
    ENTITY_NAME_SEPARATORS_REGEX = re.compile(fr'''[{'|'.join(ENTITY_NAME_SEPARATORS)}]''')

    def __init__(self):
        pass

    @abstractmethod
    def convert_dir(self):
        pass

    @staticmethod
    def get_entities_by_entity_type(entities: Union[Iterator[LayoutObject], Iterator[Classifier]],
                                    entity_type: FileType) -> Union[List[LayoutObject], List[Classifier]]:
        """
        Returns all entities in the given pack whom entity type matches the 'entity_type' argument given.
        Args:
            entities (Union[Iterator[LayoutObject], Iterator[Classifier]]): Entities.
            entity_type (FileType): The entity type.

        Returns:
            (Union[List[LayoutObject], List[Classifier]]): List of entities whom type matches 'entity_type'.
        """
        return [entity for entity in entities if entity.type() == entity_type]

    def entity_separators_to_underscore(self, name: str) -> str:
        """
        Receives a string, replaces every char in 'ENTITY_NAME_SEPARATORS' with '_'.
        Examples:
            - entity_separators_to_underscore('a b_c-d') --> a_b_c_d
        Args:
            name (str): Name to replace separators with underscore.

        Returns:
            (str): The string replaced.
        """
        return re.sub(self.ENTITY_NAME_SEPARATORS_REGEX, '_', name)

    @staticmethod
    def dump_new_entity(new_entity_path: str, new_entity_dict: Dict) -> None:
        """
        Receives the path of the entity to be created, and its data represented as a dict.
        Creates a file in the expected path and with the expected data.
        Args:
            new_entity_path (str): The new entity path.
            new_entity_dict (Dict): The new entity data.

        Returns:
            (None): Creates a new file.
        """
        with open(new_entity_path, 'w') as jf:
            json.dump(obj=new_entity_dict, fp=jf, indent=2)
