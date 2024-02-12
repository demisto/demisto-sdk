from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import (
    PACK_METADATA_SUPPORT,
    PACKS_DIR,
    PACKS_PACK_META_FILE_NAME,
    PARTNER_SUPPORT,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.tools import get_pack_name, os


class AuthorImageValidator(ImageValidator):
    author_image_suffix: str = "Author_image.png"

    def __init__(
        self,
        file_path: str,
        ignored_errors=None,
        json_file_path=None,
        maximum_image_size: Optional[int] = None,
        specific_validations=None,
    ):
        super().__init__(
            file_path=file_path,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self.pack_path = os.path.join(PACKS_DIR, get_pack_name(file_path))
        self.maximum_image_size = (
            maximum_image_size if maximum_image_size else self.IMAGE_MAX_SIZE
        )

    def get_support_level(self):
        metadata_path = os.path.join(self.pack_path, PACKS_PACK_META_FILE_NAME)
        with open(metadata_path) as f:
            metadata_content = json.load(f)
            return metadata_content.get(PACK_METADATA_SUPPORT)

    @error_codes("IM109")
    def is_valid(self) -> bool:
        """
        Checks whether author image is valid.
        Returns:
            (bool): Whether author image is valid.
        """
        if Path(self.file_path).exists():
            self.validate_size(
                allow_empty_image_file=False, maximum_size=self.maximum_image_size
            )
        else:
            if self.get_support_level() == PARTNER_SUPPORT:
                error_message, error_code = Errors.author_image_is_missing(
                    self.file_path
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self._is_valid = False
        return self._is_valid
