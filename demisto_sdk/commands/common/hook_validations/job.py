from distutils.version import LooseVersion
from typing import Tuple

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator

MIN_FROM_VERSION = LooseVersion("6.5.0")


class JobValidator(ContentEntityValidator):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, json_file_path=None,
                 **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, json_file_path=json_file_path,
                         **kwargs)
        self.from_version = self.current_file.get('fromServerVersion')

    def is_valid_fromversion(self):
        if self.from_version:
            if LooseVersion(self.from_version) < MIN_FROM_VERSION:
                error_message, error_code = Errors.invalid_from_server_version_in_job(self.from_version)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True  # todo is missing from_version okay?
