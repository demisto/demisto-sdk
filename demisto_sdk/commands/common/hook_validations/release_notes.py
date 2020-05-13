from __future__ import print_function

from demisto_sdk.commands.common.tools import (get_latest_release_notes_text,
                                               get_release_notes_file_path,
                                               print_error)


class ReleaseNotesValidator:
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
        master_diff (str): the changes in the changelog file compared to origin/master.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.release_notes_path = get_release_notes_file_path(self.file_path)
        self.latest_release_notes = get_latest_release_notes_text(self.release_notes_path)

    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.latest_release_notes
        if '%%UPDATE_RN%%' in release_notes_comments:
            print_error(f"Please finish filling out the release notes found at: {self.file_path}")
            return False
        elif len(release_notes_comments) == 0:
            print_error(f"Please complete the release notes found at: {self.file_path}")
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
