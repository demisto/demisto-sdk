from __future__ import print_function

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (get_latest_release_notes_text,
                                               get_release_notes_file_path)


class ReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
        master_diff (str): the changes in the changelog file compared to origin/master.
    """

    def __init__(self, file_path, ignored_errors=None, print_as_warnings=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.file_path = file_path
        self.release_notes_path = get_release_notes_file_path(self.file_path)
        self.latest_release_notes = get_latest_release_notes_text(self.release_notes_path)

    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.latest_release_notes
        if '%%UPDATE_RN%%' in release_notes_comments:
            error_message, error_code = Errors.release_notes_not_finished(self.file_path)
            if self.handle_error(error_message, error_code):
                return False
        elif len(release_notes_comments) == 0:
            error_message, error_code = Errors.release_notes_file_empty(self.file_path)
            if self.handle_error(error_message, error_code):
                return False
        return True

    def is_file_valid(self):
        """Checks if given file is valid.

        Return:
            bool. True if file's release notes are valid, False otherwise.
        """
        validations = [
            self.has_release_notes_been_filled_out()
        ]

        return all(validations)
