from __future__ import print_function

import glob
import os
import re

from demisto_sdk.common.hook_validations.pack_unique_files import PackUniqueFilesValidator
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.constants import CODE_FILES_REGEX, OLD_YML_FORMAT_FILE, SCHEMA_REGEX, KNOWN_FILE_STATUSES, \
    IGNORED_TYPES_REGEXES, INTEGRATION_REGEX, BETA_INTEGRATION_REGEX, BETA_INTEGRATION_YML_REGEX, SCRIPT_REGEX, \
    IMAGE_REGEX, INCIDENT_FIELD_REGEX, TEST_PLAYBOOK_REGEX, \
    INTEGRATION_YML_REGEX, DIR_LIST, PACKAGE_SUPPORTING_DIRECTORIES, \
    YML_BETA_INTEGRATIONS_REGEXES, PACKAGE_SCRIPTS_REGEXES, YML_INTEGRATION_REGEXES, PACKS_DIR, PACKS_DIRECTORIES, \
    Errors
from demisto_sdk.common.hook_validations.conf_json import ConfJsonValidator
from demisto_sdk.common.hook_validations.description import DescriptionValidator
from demisto_sdk.common.hook_validations.id import IDSetValidator
from demisto_sdk.common.hook_validations.image import ImageValidator
from demisto_sdk.common.hook_validations.incident_field import IncidentFieldValidator
from demisto_sdk.common.hook_validations.integration import IntegrationValidator
from demisto_sdk.common.hook_validations.script import ScriptValidator
from demisto_sdk.common.hook_validations.structure import StructureValidator
from demisto_sdk.common.tools import checked_type, run_command, print_error, print_warning, print_color, \
    LOG_COLORS, get_yaml, filter_packagify_changes, collect_ids, str2bool, get_pack_name, is_file_path_in_pack, \
    get_latest_release_notes_text, get_release_notes_file_path
from demisto_sdk.yaml_tools.unifier import Unifier


class ReleaseNotesValidator:
    """Release notes validator is designed to validate the existence and correctness of the release notes we enter to content repo.

            Attributes:
                file_path (str): the path to the file we are examining at the moment.
                is_valid (bool): the attribute which saves the valid/in-valid status of the current file. will be bool
                                only after running is_file_valid.
            """

    def __init__(self, file_path):
        # type: (str) -> None
        self.file_path = file_path
        self._is_valid = None  # type: Optional[bool]

    @staticmethod
    def is_valid_release_notes_structure(rn):
        # regex meaning: dont start with any of the characters in the first []
        #                start with a letter or number
        #                end with '.'
        one_line_rn_regex = r'[^\r\n\t\f\v\ \_\-][a-zA-Z0-9].*\.$'

        # regex meaning: start with tab, then '-' then space
        #                end with '.'
        multi_line_rn_regex = r'(\t| {2,4})+(\- .*\.$|\- ?$)'

        rn_comments = rn.split('\n')
        if len(rn_comments) == 1:
            if not (rn == '-' or re.match(one_line_rn_regex, rn)):
                return False

        else:
            # if it's one line comment with list
            if re.match(one_line_rn_regex, rn_comments[0]):
                rn_comments = rn_comments[1:]

            for comment in rn_comments:
                if not re.match(multi_line_rn_regex, comment):
                    return False

        return True

    def validate_file_release_notes(self):
        """Validate that the file has proper release notes when modified.

        This function updates the class attribute self._is_valid instead of passing it back and forth.
        """
        rn_standard = 'https://github.com/demisto/content/blob/master/docs/release_notes/README.md'

        if self.is_renamed:
            print_warning("You might need RN please make sure to check that.")
            self._is_valid = True
            return

        if os.path.isfile(self.file_path):
            rn_path = get_release_notes_file_path(self.file_path)
            rn = get_latest_release_notes_text(rn_path)

            # check rn file exists and contain text
            if rn is None:
                print_error('File {} is missing releaseNotes, Please add it under {}'.format(self.file_path, rn_path))
                self._is_valid = False

            # check if file structure matches the convention
            if not self.is_valid_release_notes_structure(rn):
                print_error('File {} is not formatted according to release notes standards.\n'
                            'Fix according to {}'.format(rn_path, rn_standard))
                self._is_valid = False
