from distutils.version import LooseVersion

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION, WIZARD, FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class WizardValidator(ContentEntityValidator):

    def __init__(self, structure_validator, ignored_errors=False, print_as_warnings=False, json_file_path=None,
                 **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, json_file_path=json_file_path,
                         **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self._errors = []

    def get_errors(self):
        return "\n".join(self._errors)

    def is_valid_version(self):
        # not validated
        return True

    def is_valid_fromversion(self):
        if not self.from_version or LooseVersion(self.from_version) < LooseVersion(FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.WIZARD)):
            error_message, error_code = Errors.invalid_fromversion_in_wizard(self.from_version)
            formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
            if formatted_error:
                self._errors.append(error_message)
                return False
        return True

    def is_valid_integrations(self):
        #TODO: Implement
        pass

    def is_valid_playbooks(self):
        #TODO: Implement
        pass

    def is_valid_file(self, validate_rn=True):
        return all((
            self._is_id_equals_name(WIZARD),
            self.is_valid_integrations(),
            self.is_valid_playbooks(),
            super().is_valid_file(validate_rn),  # includes is_valid_fromversion()
        ))
