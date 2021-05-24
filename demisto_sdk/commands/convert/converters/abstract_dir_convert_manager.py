import os
from abc import abstractmethod

from packaging.version import Version

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack


class AbstractDirConvertManager:
    def __init__(self, pack: Pack, input_path: str, server_version: Version, entity_dir_name: str = ''):
        self.pack = pack
        self.input_path = input_path
        self.server_version = server_version
        self.entity_dir_name = entity_dir_name

    @abstractmethod
    def convert(self):
        pass

    def should_convert(self) -> bool:
        """
        Checks whether conversion should be done or not. Uses the 'entity_dir_name' received in init function
        by the inheriting class.
        Conversion should happen if one of the 2 cases occur:
        1) The input path for conversion is the whole pack
        2) The input path for conversion ends with the corresponding dir given in 'entity_dir_name'.
        Returns:
            (bool):
            - True if conversion should be done.
            - False if conversion should not be done.
        """
        return self.is_dir_convert_manager_path() or self.is_pack_path()

    def is_pack_path(self) -> bool:
        """
        Checks whether pack given in input path is for a pack.
        Examples
            - self.input_path = 'Packs/BitcoinAbuse
              Returns: True
            - self.input_path = 'Packs/BitcoinAbuse/Layouts'
              Returns: False
        Returns:
            (bool):
            - True if the input path is for a given pack.
            - False if the input path is not for a given pack.
        """
        return os.path.basename(os.path.dirname(self.input_path)) == PACKS_DIR

    def is_dir_convert_manager_path(self) -> bool:
        """
        Checks whether path given ends the 'entity_dir_name' field.
        Examples
            - self.input_path = 'Packs/BitcoinAbuse
              self.entity_dir_name = 'Layouts'
              Returns: False
            - self.input_path = 'Packs/BitcoinAbuse/Classifiers
              self.entity_dir_name = 'Layouts'
              Returns: False
            - self.input_path = 'Packs/BitcoinAbuse/Layouts
              self.entity_dir_name = 'Layouts'
              Returns: True
        Returns:
            (bool):
            - True if the path ends with 'entity_dir_name'.
            - False if path does not end with 'entity_dir_name'.
        """
        # TODO validate outside input is not empty
        return os.path.basename(self.input_path) == self.entity_dir_name
