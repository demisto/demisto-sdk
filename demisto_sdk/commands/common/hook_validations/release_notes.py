from __future__ import print_function

import itertools

from demisto_sdk.commands.common.constants import VALIDATED_PACK_ITEM_TYPES
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (get_latest_release_notes_text,
                                               get_release_notes_file_path)
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
        master_diff (str): the changes in the changelog file compared to origin/master.
    """

    def __init__(self, file_path, modified_files=None, pack_name=None, added_files=None, ignored_errors=None,
                 print_as_warnings=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.file_path = file_path
        self.modified_files = modified_files
        self.added_files = added_files
        self.pack_name = pack_name
        self.release_notes_path = get_release_notes_file_path(self.file_path)
        self.latest_release_notes = get_latest_release_notes_text(self.release_notes_path)

    def are_release_notes_complete(self):
        is_valid = True
        modified_added_files = itertools.chain.from_iterable((self.added_files or [], self.modified_files or []))
        if modified_added_files:
            for file in modified_added_files:
                if not (permitted_type in file for permitted_type in VALIDATED_PACK_ITEM_TYPES):
                    continue
                elif self.pack_name in file:
                    update_rn_util = UpdateRN(pack=self.pack_name, pack_files=set(), update_type=None, added_files=set())
                    file_name, file_type = update_rn_util.identify_changed_file_type(file)
                    if file_name and file_type:
                        if (file_type not in self.latest_release_notes) and (file_name not in self.latest_release_notes):
                            error_message, error_code = Errors.missing_release_notes_entry(file_type, self.pack_name)
                            if self.handle_error(error_message, error_code, self.file_path):
                                is_valid = False
        return is_valid

    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.latest_release_notes
        if len(release_notes_comments) == 0:
            error_message, error_code = Errors.release_notes_file_empty()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        elif '%%UPDATE_RN%%' in release_notes_comments:
            error_message, error_code = Errors.release_notes_not_finished()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_file_valid(self):
        """Checks if given file is valid.

        Return:
            bool. True if file's release notes are valid, False otherwise.
        """
        validations = [
            self.has_release_notes_been_filled_out(),
            self.are_release_notes_complete()
        ]

        return all(validations)
