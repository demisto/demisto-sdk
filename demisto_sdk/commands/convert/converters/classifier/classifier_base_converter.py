import re
from abc import abstractmethod

from demisto_sdk.commands.common.constants import ENTITY_NAME_SEPARATORS
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.base_converter import \
    BaseConverter


class ClassifierBaseConverter(BaseConverter):
    ENTITY_NAME_SEPARATORS_REGEX = re.compile(fr'''[{'|'.join(ENTITY_NAME_SEPARATORS)}]''')

    def __init__(self, pack: Pack):
        super().__init__()
        self.pack = pack

    @abstractmethod
    def convert_dir(self) -> int:
        pass

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
