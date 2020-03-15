import os
import re
from abc import abstractmethod

from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.tools import print_error, get_release_notes_file_path, \
    get_latest_release_notes_text, run_command
from demisto_sdk.commands.common.constants import ID_IN_COMMONFIELDS, ID_IN_ROOT


class BaseValidator:
    DEFAULT_VERSION = -1

    def __init__(self, structure_validator):
        # type: (StructureValidator) -> None
        self.structure_validator = structure_validator
        self.current_file = structure_validator.current_file
        self.old_file = structure_validator.old_file
        self.file_path = structure_validator.file_path
        self.is_valid = structure_validator.is_valid

    def is_valid_file(self, validate_rn=True):
        tests = [
            self.is_valid_version()
        ]
        # In case of release branch we allow to remove release notes
        if validate_rn and not self.is_release_branch():
            tests.append(self.is_there_release_notes())
        return all(tests)

    @abstractmethod
    def is_valid_version(self):
        # type: () -> bool
        pass

    def _is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.current_file.get('version') != self.DEFAULT_VERSION:
            print_error(Errors.wrong_version(self.file_path, self.DEFAULT_VERSION))
            self.is_valid = False
            return False
        return True

    def is_there_release_notes(self):
        """Validate that the file has proper release notes when modified.
        This function updates the class attribute self._is_valid.

        Returns:
            (bool): is there release notes
        """
        if os.path.isfile(self.file_path):
            rn_path = get_release_notes_file_path(self.file_path)
            release_notes = get_latest_release_notes_text(rn_path)

            # check release_notes file exists and contain text
            if release_notes is None:
                self.is_valid = False
                print_error("Missing release notes for: {}".format(self.file_path))
                return False
        return True

    @staticmethod
    def is_release_branch():
        # type: () -> bool
        """Check if we are working on a release branch.

        Returns:
            (bool): is release branch
        """
        diff_string_config_yml = run_command("git diff origin/master .circleci/config.yml")
        if re.search(r'[+-][ ]+CONTENT_VERSION: ".*', diff_string_config_yml):
            return True
        return False

    @staticmethod
    def is_subset_dictionary(new_dict, old_dict):
        # type: (dict, dict) -> bool
        """Check if the new dictionary is a sub set of the old dictionary.

        Args:
            new_dict (dict): current branch result from _get_command_to_args
            old_dict (dict): master branch result from _get_command_to_args

        Returns:
            bool. Whether the new dictionary is a sub set of the old dictionary.
        """
        for arg, required in old_dict.items():
            if arg not in new_dict.keys():
                return False

            if required != new_dict[arg] and new_dict[arg]:
                return False

        for arg, required in new_dict.items():
            if arg not in old_dict.keys() and required:
                return False
        return True

    def _get_file_id(self, file_type):
        file_id = ''
        if file_type in ID_IN_ROOT:
            file_id = self.current_file.get('id')
        elif file_type in ID_IN_COMMONFIELDS:
            file_id = self.current_file.get('commonfields', {}).get('id')
        return file_id

    def _is_id_equals_name(self, file_type):
        """Validate that the id of the file equals to the name.
         Args:
            file_type (str): the file type. can be 'integration', 'script', 'playbook', 'dashboard', 'id'

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self._get_file_id(file_type)
        name = self.current_file.get('name', '')
        if file_id != name:
            print_error("The File's name, which is: '{0}', should be equal to its ID, which is: '{1}'."
                        " please update the file (path to file: {2}).".format(name, file_id, self.file_path))
            return False
        return True
