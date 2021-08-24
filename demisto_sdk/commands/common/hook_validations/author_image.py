import json
from typing import Optional

from demisto_sdk.commands.common.constants import (PACK_METADATA_SUPPORT,
                                                   PACKS_DIR,
                                                   PACKS_PACK_META_FILE_NAME)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.tools import get_pack_name, os


class AuthorImageValidator(ImageValidator):
    author_image_suffix: str = 'Author_image.png'

    def __init__(self, file_path: str, ignored_errors=None, print_as_warnings=False,
                 suppress_print=False, json_file_path=None, maximum_image_size: Optional[int] = None):
        super().__init__(file_path=file_path, ignored_errors=ignored_errors,
                         print_as_warnings=print_as_warnings, suppress_print=suppress_print,
                         json_file_path=json_file_path)
        self.pack_path = os.path.join(PACKS_DIR, get_pack_name(file_path))
        self.maximum_image_size = maximum_image_size if maximum_image_size else self.IMAGE_MAX_SIZE

    def get_support_level(self):
        metadata_path = os.path.join(self.pack_path, PACKS_PACK_META_FILE_NAME)
        with open(metadata_path, 'r') as f:
            metadata_content = json.load(f)
            return metadata_content.get(PACK_METADATA_SUPPORT)

    def is_valid(self) -> bool:
        """
        Checks whether author image is valid.
        Returns:
            (bool): Whether author image is valid.
        """
        if os.path.exists(self.file_path):
            self.validate_size(allow_empty_image_file=False, maximum_size=self.maximum_image_size)
        else:
            if self.get_support_level() == 'partner':
                error_message, error_code = Errors.author_image_is_missing(self.file_path)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False
        return self._is_valid
