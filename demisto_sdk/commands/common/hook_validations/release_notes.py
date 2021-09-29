from __future__ import print_function

import itertools
import os
import re

from demisto_sdk.commands.common.constants import (
    PACKS_DIR, RN_HEADER_BY_FILE_TYPE, SKIP_RELEASE_NOTES_FOR_TYPES)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (find_type,
                                               get_latest_release_notes_text,
                                               get_pack_name,
                                               get_release_notes_file_path)
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        release_notes_file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
    """

    def __init__(self, release_notes_file_path, modified_files=None, pack_name=None, added_files=None, ignored_errors=None,
                 print_as_warnings=False, suppress_print=False, json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.release_notes_file_path = release_notes_file_path
        self.modified_files = modified_files
        self.added_files = added_files
        self.pack_name = pack_name
        self.pack_path = os.path.join(PACKS_DIR, self.pack_name)
        self.release_notes_path = get_release_notes_file_path(self.release_notes_file_path)
        self.latest_release_notes = get_latest_release_notes_text(self.release_notes_path)
        self.file_types_that_should_not_appear_in_rn = SKIP_RELEASE_NOTES_FOR_TYPES

    def are_release_notes_complete(self):
        is_valid = True
        modified_added_files = itertools.chain.from_iterable((self.added_files or [], self.modified_files or []))
        if modified_added_files:
            for file in modified_added_files:
                # renamed files will appear in the modified list as a tuple: (old path, new path)
                if isinstance(file, tuple):
                    file = file[1]
                checked_file_pack_name = get_pack_name(file)

                if find_type(file) in self.file_types_that_should_not_appear_in_rn:
                    continue
                elif checked_file_pack_name and checked_file_pack_name == self.pack_name:
                    # Refer image and description file paths to the corresponding yml files
                    file = UpdateRN.change_image_or_desc_file_path(file)
                    update_rn_util = UpdateRN(pack_path=self.pack_path, modified_files_in_pack=set(),
                                              update_type=None, added_files=set(), pack=self.pack_name)
                    file_name, file_type = update_rn_util.get_changed_file_name_and_type(file)
                    if file_name and file_type:
                        if (RN_HEADER_BY_FILE_TYPE[file_type] not in self.latest_release_notes) or \
                                (file_name not in self.latest_release_notes):
                            entity_name = update_rn_util.get_display_name(file)
                            error_message, error_code = Errors.missing_release_notes_entry(file_type, self.pack_name,
                                                                                           entity_name)
                            if self.handle_error(error_message, error_code, self.release_notes_file_path):
                                is_valid = False
        return is_valid

    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.strip_exclusion_tag(self.latest_release_notes)
        if len(release_notes_comments) == 0:
            error_message, error_code = Errors.release_notes_file_empty()
            if self.handle_error(error_message, error_code, file_path=self.release_notes_file_path):
                return False
        elif '%%UPDATE_RN%%' in release_notes_comments:
            error_message, error_code = Errors.release_notes_not_finished()
            if self.handle_error(error_message, error_code, file_path=self.release_notes_file_path):
                return False
        return True

    @staticmethod
    def strip_exclusion_tag(release_notes_comments):
        """
        Strips the exclusion tag (<!-- -->) from the release notes since release notes should never
        be empty as this is poor user experience.
        Return:
            str. Cleaned notes with tags and contained notes removed.
        """
        return re.sub(r'<\!--.*?-->', '', release_notes_comments, flags=re.DOTALL)

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
