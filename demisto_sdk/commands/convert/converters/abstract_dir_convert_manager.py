from abc import abstractmethod
import os
from demisto_sdk.commands.common.constants import PACKS_DIR


class AbstractDirConvertManager:
    def __init__(self, input_path: str, server_version: str, entity_dir_name: str = ''):
        self.input_path = input_path
        self.server_version = server_version
        self.entity_dir_name = entity_dir_name

    @abstractmethod
    def convert(self):
        pass

    def should_convert(self) -> bool:
        return self.is_dir_convert_manager_path() or self.is_pack_path()

    def is_pack_path(self) -> bool:
        return os.path.basename(os.path.dirname(self.input_path)) == PACKS_DIR

    def is_dir_convert_manager_path(self):
        # TODO validate outside input is not empty
        return os.path.basename(self.input_path) == self.entity_dir_name
