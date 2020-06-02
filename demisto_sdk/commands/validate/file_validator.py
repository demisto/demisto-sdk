"""
This script is used to validate the files in Content repository. Specifically for each file:
1) Proper prefix
2) Proper suffix
3) Valid yml/json schema
4) Having ReleaseNotes if applicable.

It can be run to check only committed changes (if the first argument is 'true') or all the files in the repo.
Note - if it is run for all the files in the repo it won't check releaseNotes, use `old_release_notes.py`
for that task.
"""
from __future__ import print_function

import os
import re
from configparser import ConfigParser, MissingSectionHeaderError
from glob import glob

import click
import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, BETA_INTEGRATION_REGEX,
    BETA_INTEGRATION_YML_REGEX, CHECKED_TYPES_REGEXES, CODE_FILES_REGEX,
    CONTENT_ENTITIES_DIRS, IGNORED_TYPES_REGEXES, IMAGE_REGEX,
    INTEGRATION_REGEX, INTEGRATION_REGXES, JSON_ALL_CLASSIFIER_REGEXES,
    JSON_ALL_CLASSIFIER_REGEXES_5_9_9, JSON_ALL_DASHBOARDS_REGEXES,
    JSON_ALL_INCIDENT_TYPES_REGEXES, JSON_ALL_INDICATOR_TYPES_REGEXES,
    JSON_ALL_LAYOUT_REGEXES, JSON_ALL_MAPPER_REGEXES,
    JSON_INDICATOR_AND_INCIDENT_FIELDS, KNOWN_FILE_STATUSES,
    OLD_YML_FORMAT_FILE, PACKAGE_SCRIPTS_REGEXES, PACKS_DIR,
    PACKS_PACK_IGNORE_FILE_NAME, PACKS_RELEASE_NOTES_REGEX, PLAYBOOK_REGEX,
    PLAYBOOKS_REGEXES_LIST, SCHEMA_REGEX, SCRIPT_REGEX, TEST_PLAYBOOK_REGEX,
    YML_ALL_SCRIPTS_REGEXES, YML_BETA_INTEGRATIONS_REGEXES,
    YML_INTEGRATION_REGEXES)
from demisto_sdk.commands.common.errors import (ERROR_CODE,
                                                PRESET_ERROR_TO_CHECK,
                                                PRESET_ERROR_TO_IGNORE, Errors)
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.classifier import \
    ClassifierValidator
from demisto_sdk.commands.common.hook_validations.conf_json import \
    ConfJsonValidator
from demisto_sdk.commands.common.hook_validations.dashboard import \
    DashboardValidator
from demisto_sdk.commands.common.hook_validations.id import IDSetValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.incident_field import \
    IncidentFieldValidator
from demisto_sdk.commands.common.hook_validations.incident_type import \
    IncidentTypeValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
from demisto_sdk.commands.common.hook_validations.mapper import MapperValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.hook_validations.release_notes import \
    ReleaseNotesValidator
from demisto_sdk.commands.common.hook_validations.reputation import \
    ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, checked_type,
                                               filter_packagify_changes,
                                               find_type, get_pack_name,
                                               get_remote_file, get_yaml,
                                               is_file_path_in_pack,
                                               print_color, print_error,
                                               print_warning, run_command,
                                               should_file_skip_validation)
from demisto_sdk.commands.unify.unifier import Unifier


class FilesValidator:
    """FilesValidator is a class that's designed to validate all the changed files on your branch, and all files in case
    you are on master, this class will be used on your local env as the validation hook(pre-commit), and on CircleCi
    to make sure you did not bypass the hooks as a safety precaution.
    Attributes:
        is_backward_check (bool): Whether to check for backwards compatibility.
        prev_ver (str): If using git, holds the branch to compare the current one to. Default is origin/master.
        use_git (bool): Whether to use git or not.
        is_circle: (bool): Whether the validation was initiated by CircleCI or not.
        print_ignored_files (bool): Whether to print the files that were ignored during the validation or not.
        skip_conf_json (bool): Whether to validate conf.json or not.
        validate_id_set (bool): Whether to validate id_set or not.
        file_path (string): If validating a specific file, golds it's path.
        validate_all (bool) Whether to validate all files or not.
        configuration (Configuration): Configurations for IDSetValidator.
    """

    def __init__(self, is_backward_check=True, prev_ver=None, use_git=False, only_committed_files=False,
                 print_ignored_files=False, skip_conf_json=True, validate_id_set=False, file_path=None,
                 validate_all=False, is_private_repo=False, skip_pack_rn_validation=False, print_ignored_errors=False,
                 configuration=Configuration()):
        self.validate_all = validate_all
        self.branch_name = ''
        self.use_git = use_git
        self.skip_pack_rn_validation = skip_pack_rn_validation
        if self.use_git:
            print('Using git')
            self.branch_name = self.get_current_working_branch()
            print(f'Running validation on branch {self.branch_name}')
            if self.branch_name in ['master', 'test-sdk-master']:
                self.skip_pack_rn_validation = True

        self.prev_ver = prev_ver
        self._is_valid = True
        self.configuration = configuration
        self.is_backward_check = is_backward_check
        self.is_circle = only_committed_files
        self.print_ignored_files = print_ignored_files
        self.skip_conf_json = skip_conf_json
        self.validate_id_set = validate_id_set
        self.file_path = file_path
        self.changed_pack_data = set()

        self.is_private_repo = is_private_repo
        if is_private_repo:
            print('Running in a private repository')
            self.skip_conf_json = True  # private repository don't have conf.json file

        if not self.skip_conf_json:
            self.conf_json_validator = ConfJsonValidator()

        if self.validate_id_set:
            self.id_set_validator = IDSetValidator(is_circle=self.is_circle, configuration=self.configuration)

        self.handle_error = BaseValidator().handle_error
        self.print_ignored_errors = print_ignored_errors

    def run(self):
        print_color('Starting validating files structure', LOG_COLORS.GREEN)
        if self.is_valid_structure():
            print_color('The files are valid', LOG_COLORS.GREEN)
            return 0
        else:
            print_color('The files were found as invalid, the exact error message can be located above', LOG_COLORS.RED)
            return 1

    @staticmethod
    def get_current_working_branch():
        branches = run_command('git branch')
        branch_name_reg = re.search(r'\* (.*)', branches)
        return branch_name_reg.group(1)

    @staticmethod
    def get_modified_files(files_string, tag='master', print_ignored_files=False):
        """Get lists of the modified files in your branch according to the files string.

        Args:
            files_string (string): String that was calculated by git using `git diff` command.
            tag (string): String of git tag used to update modified files.
            print_ignored_files (bool): should print ignored files.

        Returns:
            (modified_files_list, added_files_list, deleted_files). Tuple of sets.
        """
        all_files = files_string.split('\n')
        deleted_files = set()
        added_files_list = set()
        modified_files_list = set()
        old_format_files = set()
        for f in all_files:
            file_data = f.split()
            if not file_data:
                continue

            file_status = file_data[0]
            file_path = file_data[1]

            if file_status.lower().startswith('r'):
                file_status = 'r'
                file_path = file_data[2]

            if checked_type(file_path, CODE_FILES_REGEX) and file_status.lower() != 'd' \
                    and not file_path.endswith('_test.py'):
                # naming convention - code file and yml file in packages must have same name.
                file_path = os.path.splitext(file_path)[0] + '.yml'
            elif file_path.endswith('.js') or file_path.endswith('.py'):
                continue
            if file_status.lower() == 'd' and checked_type(file_path) and not file_path.startswith('.'):
                deleted_files.add(file_path)
            elif not os.path.isfile(file_path):
                continue
            elif file_status.lower() in ['m', 'a', 'r'] and checked_type(file_path, OLD_YML_FORMAT_FILE) and \
                    FilesValidator._is_py_script_or_integration(file_path):
                old_format_files.add(file_path)
            elif file_status.lower() == 'm' and checked_type(file_path) and not file_path.startswith('.'):
                modified_files_list.add(file_path)
            elif file_status.lower() == 'a' and checked_type(file_path) and not file_path.startswith('.'):
                added_files_list.add(file_path)
            elif file_status.lower().startswith('r') and checked_type(file_path):
                # if a code file changed, take the associated yml file.
                if checked_type(file_data[2], CODE_FILES_REGEX):
                    modified_files_list.add(file_path)
                else:
                    modified_files_list.add((file_data[1], file_data[2]))

            elif checked_type(file_path, [SCHEMA_REGEX]):
                modified_files_list.add(file_path)

            elif file_status.lower() not in KNOWN_FILE_STATUSES:
                print_error('{} file status is an unknown one, please check. File status was: {}'
                            .format(file_path, file_status))

            elif print_ignored_files and not checked_type(file_path, IGNORED_TYPES_REGEXES):
                print_warning('Ignoring file path: {}'.format(file_path))

        modified_files_list, added_files_list, deleted_files = filter_packagify_changes(
            modified_files_list,
            added_files_list,
            deleted_files,
            tag)

        return modified_files_list, added_files_list, deleted_files, old_format_files

    def get_modified_and_added_files(self, tag='origin/master'):
        """Get lists of the modified and added files in your branch according to the git diff output.

        Args:
            tag (string): String of git tag used to update modified files

        Returns:
            (modified_files, added_files). Tuple of sets.
        """
        # Two dots is the default in git diff, it will compare with the last known commit as the base
        # Three dots will compare with the last known shared commit as the base
        compare_type = '.' if 'master' in tag else ''
        all_changed_files_string = run_command(
            'git diff --name-status {tag}..{compare_type}refs/heads/{branch}'.format(tag=tag,
                                                                                     branch=self.branch_name,
                                                                                     compare_type=compare_type))
        modified_files, added_files, _, old_format_files = self.get_modified_files(
            all_changed_files_string,
            tag=tag,
            print_ignored_files=self.print_ignored_files)

        if not self.is_circle:
            files_string = run_command('git diff --name-status --no-merges HEAD')
            nc_modified_files, nc_added_files, nc_deleted_files, nc_old_format_files = self.get_modified_files(
                files_string, print_ignored_files=self.print_ignored_files)

            all_changed_files_string = run_command('git diff --name-status {}'.format(tag))
            modified_files_from_tag, added_files_from_tag, _, _ = \
                self.get_modified_files(all_changed_files_string,
                                        print_ignored_files=self.print_ignored_files)

            if self.file_path:
                if F'M\t{self.file_path}' in files_string:
                    modified_files = {self.file_path}
                    added_files = set()
                else:
                    modified_files = set()
                    added_files = {self.file_path}
                return modified_files, added_files, set(), set()

            old_format_files = old_format_files.union(nc_old_format_files)
            modified_files = modified_files.union(
                modified_files_from_tag.intersection(nc_modified_files))

            added_files = added_files.union(
                added_files_from_tag.intersection(nc_added_files))

            modified_files = modified_files - set(nc_deleted_files)
            added_files = added_files - set(nc_modified_files) - set(nc_deleted_files)

        changed_files = modified_files.union(added_files)
        packs = self.get_packs(changed_files)

        return modified_files, added_files, old_format_files, packs

    @staticmethod
    def get_packs(changed_files):
        packs = set()
        for changed_file in changed_files:
            if isinstance(changed_file, tuple):
                changed_file = changed_file[1]
            pack = get_pack_name(changed_file)
            if pack and is_file_path_in_pack(changed_file):
                packs.add(pack)

        return packs

    def is_valid_release_notes(self, file_path, pack_name=None, modified_files=None, added_files=None,
                               ignored_errors_list=None):
        release_notes_validator = ReleaseNotesValidator(file_path, pack_name=pack_name,
                                                        modified_files=modified_files, added_files=added_files,
                                                        ignored_errors=ignored_errors_list,
                                                        print_as_warnings=self.print_ignored_errors)
        if not release_notes_validator.is_file_valid():
            self._is_valid = False

    def validate_modified_files(self, modified_files, tag='master'):  # noqa: C901
        """Validate the modified files from your branch.

        In case we encounter an invalid file we set the self._is_valid param to False.

        Args:
            modified_files (set): A set of the modified files in the current branch.
            tag (str): The reference point to the branch with which we are comparing the modified files.
        """
        _modified_files = set()
        for mod_file in modified_files:
            if isinstance(mod_file, tuple):
                continue
            if not any(non_permitted_type in mod_file.lower() for non_permitted_type in ALL_FILES_VALIDATION_IGNORE_WHITELIST):
                if 'ReleaseNotes' not in mod_file.lower():
                    _modified_files.add(mod_file)
        changed_packs = self.get_packs(_modified_files)
        for file_path in modified_files:
            old_file_path = None
            # modified_files are returning from running git diff.
            # If modified file was renamed\moved, file_path could be a tuple containing original path and new path
            if isinstance(file_path, tuple):
                old_file_path, file_path = file_path
            file_type = find_type(file_path)
            pack_name = get_pack_name(file_path)
            ignored_errors_list = self.get_error_ignore_list(pack_name)
            # unified files should not be validated
            if file_path.endswith('_unified.yml'):
                continue
            print('\nValidating {}'.format(file_path))
            if not checked_type(file_path):
                print_warning('- Skipping validation of non-content entity file.')
                continue

            if re.search(TEST_PLAYBOOK_REGEX, file_path, re.IGNORECASE):
                continue

            elif 'README' in file_path:
                readme_validator = ReadMeValidator(file_path, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                if not readme_validator.is_valid_file():
                    self._is_valid = False
                continue

            structure_validator = StructureValidator(file_path, old_file_path=old_file_path,
                                                     ignored_errors=ignored_errors_list,
                                                     print_as_warnings=self.print_ignored_errors, tag=tag)
            if not structure_validator.is_valid_file():
                self._is_valid = False

            if self.validate_id_set:
                if not self.id_set_validator.is_file_valid_in_set(file_path):
                    self._is_valid = False

            elif checked_type(file_path, YML_INTEGRATION_REGEXES) or file_type == 'integration':
                integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                             print_as_warnings=self.print_ignored_errors,
                                                             branch_name=self.branch_name)
                if self.is_backward_check and not integration_validator.is_backward_compatible():
                    self._is_valid = False

                if not integration_validator.is_valid_file():
                    self._is_valid = False

            elif checked_type(file_path, YML_BETA_INTEGRATIONS_REGEXES) or file_type == 'betaintegration':
                integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                             print_as_warnings=self.print_ignored_errors,
                                                             branch_name=self.branch_name)
                if not integration_validator.is_valid_beta_integration():
                    self._is_valid = False

            elif checked_type(file_path, [SCRIPT_REGEX]):
                script_validator = ScriptValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors,
                                                   branch_name=self.branch_name)
                if self.is_backward_check and not script_validator.is_backward_compatible():
                    self._is_valid = False
                if not script_validator.is_valid_file():
                    self._is_valid = False
            elif checked_type(file_path, PLAYBOOKS_REGEXES_LIST) or file_type == 'playbook':
                playbook_validator = PlaybookValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                       print_as_warnings=self.print_ignored_errors)
                if not playbook_validator.is_valid_playbook(is_new_playbook=False):
                    self._is_valid = False

            elif checked_type(file_path, PACKAGE_SCRIPTS_REGEXES):
                unifier = Unifier(os.path.dirname(file_path))
                yml_path, _ = unifier.get_script_or_integration_package_data()
                # Set file path to the yml file
                structure_validator.file_path = yml_path
                script_validator = ScriptValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors,
                                                   branch_name=self.branch_name)
                if self.is_backward_check and not script_validator.is_backward_compatible():
                    self._is_valid = False

                if not script_validator.is_valid_file():
                    self._is_valid = False

            elif re.match(IMAGE_REGEX, file_path, re.IGNORECASE):
                image_validator = ImageValidator(file_path, ignored_errors=ignored_errors_list,
                                                 print_as_warnings=self.print_ignored_errors)
                if not image_validator.is_valid():
                    self._is_valid = False

            # incident fields and indicator fields are using the same scheme.
            elif checked_type(file_path, JSON_INDICATOR_AND_INCIDENT_FIELDS):
                incident_field_validator = IncidentFieldValidator(structure_validator,
                                                                  ignored_errors=ignored_errors_list,
                                                                  print_as_warnings=self.print_ignored_errors)
                if not incident_field_validator.is_valid_file(validate_rn=True):
                    self._is_valid = False
                if self.is_backward_check and not incident_field_validator.is_backward_compatible():
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_INDICATOR_TYPES_REGEXES):
                reputation_validator = ReputationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not reputation_validator.is_valid_file(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_LAYOUT_REGEXES):
                layout_validator = LayoutValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                if not layout_validator.is_valid_layout(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_DASHBOARDS_REGEXES):
                dashboard_validator = DashboardValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                         print_as_warnings=self.print_ignored_errors)
                if not dashboard_validator.is_valid_dashboard(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_INCIDENT_TYPES_REGEXES):
                incident_type_validator = IncidentTypeValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                                print_as_warnings=self.print_ignored_errors)
                if not incident_type_validator.is_valid_incident_type(validate_rn=True):
                    self._is_valid = False
                if self.is_backward_check and not incident_type_validator.is_backward_compatible():
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES) and file_type == 'mapper':
                error_message, error_code = Errors.invalid_mapper_file_name()
                if self.handle_error(error_message, error_code, file_path=file_path):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES_5_9_9):
                classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=False,
                                                           ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not classifier_validator.is_valid_classifier(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES):
                classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=True,
                                                           ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not classifier_validator.is_valid_classifier(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_MAPPER_REGEXES):
                mapper_validator = MapperValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                if not mapper_validator.is_valid_mapper(validate_rn=True):
                    self._is_valid = False

            elif checked_type(file_path, CHECKED_TYPES_REGEXES):
                pass

            else:
                error_message, error_code = Errors.file_type_not_supported()
                if self.handle_error(error_message, error_code, file_path=file_path):
                    self._is_valid = False

        self.changed_pack_data = changed_packs

    def verify_no_dup_rn(self, added_files):
        added_rn = set()
        for file in added_files:
            if re.search(PACKS_RELEASE_NOTES_REGEX, file):
                pack_name = get_pack_name(file)
                if pack_name not in added_rn:
                    added_rn.add(pack_name)
                else:
                    error_message, error_code = Errors.multiple_release_notes_files()
                    if self.handle_error(error_message, error_code, file_path=pack_name):
                        self._is_valid = False

    def validate_added_files(self, added_files, file_type: str = None, modified_files=None):  # noqa: C901
        """Validate the added files from your branch.

        In case we encounter an invalid file we set the self._is_valid param to False.

        Args:
            added_files (set): A set of the modified files in the current branch.
            file_type (str): Used only with -p flag (the type of the file).
        """
        added_rn = set()
        self.verify_no_dup_rn(added_files)

        for file_path in added_files:
            file_type = find_type(file_path) if not file_type else file_type

            pack_name = get_pack_name(file_path)
            ignored_errors_list = self.get_error_ignore_list(pack_name)
            # unified files should not be validated
            if file_path.endswith('_unified.yml'):
                continue
            print('\nValidating {}'.format(file_path))

            if re.search(TEST_PLAYBOOK_REGEX, file_path, re.IGNORECASE) and not file_type:
                continue

            elif 'README' in file_path:
                readme_validator = ReadMeValidator(file_path, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                if not readme_validator.is_valid_file():
                    self._is_valid = False
                continue

            structure_validator = StructureValidator(file_path, is_new_file=True, predefined_scheme=file_type,
                                                     ignored_errors=ignored_errors_list,
                                                     print_as_warnings=self.print_ignored_errors)
            if not structure_validator.is_valid_file():
                self._is_valid = False

            if self.validate_id_set:
                if not self.id_set_validator.is_file_valid_in_set(file_path):
                    self._is_valid = False

                if self.id_set_validator.is_file_has_used_id(file_path):
                    self._is_valid = False

            elif re.match(PLAYBOOK_REGEX, file_path, re.IGNORECASE) or file_type == 'playbook':
                playbook_validator = PlaybookValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                       print_as_warnings=self.print_ignored_errors)
                if not playbook_validator.is_valid_playbook(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, YML_INTEGRATION_REGEXES) or file_type == 'integration':
                integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                             print_as_warnings=self.print_ignored_errors,
                                                             branch_name=self.branch_name)
                if not integration_validator.is_valid_file(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, PACKAGE_SCRIPTS_REGEXES) or file_type == 'script':
                if not file_path.endswith('.yml'):
                    unifier = Unifier(os.path.dirname(file_path))
                    yml_path, _ = unifier.get_script_or_integration_package_data()
                else:
                    yml_path = file_path
                # Set file path to the yml file
                structure_validator.file_path = yml_path
                script_validator = ScriptValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors,
                                                   branch_name=self.branch_name)

                if not script_validator.is_valid_file(validate_rn=False):
                    self._is_valid = False

            elif re.match(BETA_INTEGRATION_REGEX, file_path, re.IGNORECASE) or \
                    re.match(BETA_INTEGRATION_YML_REGEX, file_path, re.IGNORECASE) or file_type == 'betaintegration':
                integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                             print_as_warnings=self.print_ignored_errors,
                                                             branch_name=self.branch_name)
                if not integration_validator.is_valid_beta_integration(validate_rn=False):
                    self._is_valid = False

            elif re.match(IMAGE_REGEX, file_path, re.IGNORECASE):
                image_validator = ImageValidator(file_path, ignored_errors=ignored_errors_list)
                if not image_validator.is_valid():
                    self._is_valid = False

            # incident fields and indicator fields are using the same scheme.
            # TODO: add validation for classification(21630) and set validate_rn to False after issue #23398 is fixed.
            elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES_5_9_9) or file_type == 'classifier_5_9_9':
                classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=False,
                                                           ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not classifier_validator.is_valid_classifier(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES) or file_type == 'classifier':
                classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=True,
                                                           ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not classifier_validator.is_valid_classifier(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_MAPPER_REGEXES) or file_type == 'mapper':
                mapper_validator = MapperValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                if not mapper_validator.is_valid_mapper(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_INDICATOR_AND_INCIDENT_FIELDS) or \
                    file_type in ('incidentfield', 'indicatorfield'):
                incident_field_validator = IncidentFieldValidator(structure_validator,
                                                                  ignored_errors=ignored_errors_list,
                                                                  print_as_warnings=self.print_ignored_errors)
                if not incident_field_validator.is_valid_file(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_INDICATOR_TYPES_REGEXES) or file_type == 'reputation':
                reputation_validator = ReputationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                           print_as_warnings=self.print_ignored_errors)
                if not reputation_validator.is_valid_file(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_LAYOUT_REGEXES) or file_type == 'layout':
                layout_validator = LayoutValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
                # TODO: set validate_rn to False after issue #23398 is fixed.
                if not layout_validator.is_valid_layout(validate_rn=not file_type):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_DASHBOARDS_REGEXES) or file_type == 'dashboard':
                dashboard_validator = DashboardValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                         print_as_warnings=self.print_ignored_errors)
                if not dashboard_validator.is_valid_dashboard(validate_rn=False):
                    self._is_valid = False

            elif checked_type(file_path, JSON_ALL_INCIDENT_TYPES_REGEXES) or file_type == 'incidenttype':
                incident_type_validator = IncidentTypeValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                                print_as_warnings=self.print_ignored_errors)
                if not incident_type_validator.is_valid_incident_type(validate_rn=False):
                    self._is_valid = False

            elif ('ReleaseNotes' in file_path) and not self.skip_pack_rn_validation:
                added_rn.add(pack_name)
                print_color(f"Release notes found for {pack_name}", LOG_COLORS.GREEN)
                self.is_valid_release_notes(file_path, modified_files=modified_files, pack_name=pack_name,
                                            added_files=added_files, ignored_errors_list=ignored_errors_list)

            elif checked_type(file_path, CHECKED_TYPES_REGEXES):
                pass

            else:
                error_message, error_code = Errors.file_type_not_supported()
                if self.handle_error(error_message, error_code, file_path=file_path):
                    self._is_valid = False

        missing_rn = self.changed_pack_data.difference(added_rn)
        should_fail = True
        if (len(missing_rn) > 0) and (self.skip_pack_rn_validation is False):
            for pack in missing_rn:
                ignored_errors_list = self.get_error_ignore_list(pack)
                error_message, error_code = Errors.missing_release_notes_for_pack(pack)
                if not BaseValidator(ignored_errors=ignored_errors_list,
                                     print_as_warnings=self.print_ignored_errors).handle_error(
                        error_message, error_code, file_path=os.path.join(PACKS_DIR, pack)):
                    should_fail = False

            if should_fail:
                self._is_valid = False
        return self._is_valid

    def validate_no_old_format(self, old_format_files):
        """ Validate there are no files in the old format(unified yml file for the code and configuration).

        Args:
            old_format_files(set): file names which are in the old format.
        """
        invalid_files = []
        for f in old_format_files:
            yaml_data = get_yaml(f)
            if 'toversion' not in yaml_data:  # we only fail on old format if no toversion (meaning it is latest)
                invalid_files.append(f)
        if invalid_files:
            error_message, error_code = Errors.invalid_package_structure(invalid_files)
            if self.handle_error(error_message, error_code, file_path="General-Error"):
                self._is_valid = False

    def validate_committed_files(self):
        """Validate that all the committed files in your branch are valid"""
        modified_files, added_files, old_format_files, packs = self.get_modified_and_added_files()
        schema_changed = False
        for f in modified_files:
            if isinstance(f, tuple):
                _, f = f
            if checked_type(f, [SCHEMA_REGEX]):
                schema_changed = True
        # Ensure schema change did not break BC
        if schema_changed:
            print("Schema changed, validating all files")
            self.validate_all_files_schema()
        else:
            self.validate_modified_files(modified_files)
            self.validate_added_files(added_files, modified_files=modified_files)
            self.validate_no_old_format(old_format_files)
            self.validate_pack_unique_files(packs)

    def validate_pack_unique_files(self, packs: set) -> None:
        """
        Runs validations on the following pack files:
        * .secret-ignore: Validates that the file exist and that the file's secrets can be parsed as a list delimited by '\n'
        * .pack-ignore: Validates that the file exists and that all regexes in it can be compiled
        * README.md file: Validates that the file exists
        * pack_metadata.json: Validates that the file exists and that it has a valid structure
        Args:
            packs: A set of pack paths i.e {Packs/<pack-name1>, Packs/<pack-name2>}
        """
        for pack in packs:
            print(f'Validating {pack} unique pack files')
            pack_error_ignore_list = self.get_error_ignore_list(pack)
            pack_unique_files_validator = PackUniqueFilesValidator(pack, ignored_errors=pack_error_ignore_list,
                                                                   print_as_warnings=self.print_ignored_errors)
            pack_errors = pack_unique_files_validator.validate_pack_unique_files()
            if pack_errors:
                print_error(pack_errors)
                self._is_valid = False

    def run_all_validations_on_file(self, file_path: str, file_type: str = None) -> None:
        """
        Runs all validations on file specified in 'file_path'
        Args:
            file_path: A relative content path to a file to be validated
            file_type: The output of 'find_type' method
        """
        pack_name = get_pack_name(file_path)
        ignored_errors_list = self.get_error_ignore_list(pack_name)
        if 'README' in file_path:
            readme_validator = ReadMeValidator(file_path, ignored_errors=ignored_errors_list,
                                               print_as_warnings=self.print_ignored_errors)
            if not readme_validator.is_valid_file():
                self._is_valid = False
            return
        structure_validator = StructureValidator(file_path, predefined_scheme=file_type,
                                                 ignored_errors=ignored_errors_list,
                                                 print_as_warnings=self.print_ignored_errors)
        if not structure_validator.is_valid_file():
            self._is_valid = False

        elif re.match(PLAYBOOK_REGEX, file_path, re.IGNORECASE) or file_type == 'playbook':
            playbook_validator = PlaybookValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                   print_as_warnings=self.print_ignored_errors)
            if not playbook_validator.is_valid_playbook(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, INTEGRATION_REGXES) or file_type == 'integration':
            integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                         print_as_warnings=self.print_ignored_errors,
                                                         branch_name=self.branch_name)
            if not integration_validator.is_valid_file(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, YML_ALL_SCRIPTS_REGEXES) or file_type == 'script':
            # Set file path to the yml file
            structure_validator.file_path = file_path
            script_validator = ScriptValidator(structure_validator, ignored_errors=ignored_errors_list,
                                               print_as_warnings=self.print_ignored_errors,
                                               branch_name=self.branch_name)

            if not script_validator.is_valid_file(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, YML_BETA_INTEGRATIONS_REGEXES) or file_type == 'betaintegration':
            integration_validator = IntegrationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                         print_as_warnings=self.print_ignored_errors,
                                                         branch_name=self.branch_name)
            if not integration_validator.is_valid_beta_integration():
                self._is_valid = False

        # incident fields and indicator fields are using the same scheme.
        elif checked_type(file_path, JSON_INDICATOR_AND_INCIDENT_FIELDS) or \
                file_type in ('incidentfield', 'indicatorfield'):
            incident_field_validator = IncidentFieldValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                              print_as_warnings=self.print_ignored_errors)
            if not incident_field_validator.is_valid_file(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_INDICATOR_TYPES_REGEXES) or file_type == 'reputation':
            reputation_validator = ReputationValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                       print_as_warnings=self.print_ignored_errors)
            if not reputation_validator.is_valid_file(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_LAYOUT_REGEXES) or file_type == 'layout':
            layout_validator = LayoutValidator(structure_validator, ignored_errors=ignored_errors_list,
                                               print_as_warnings=self.print_ignored_errors)
            if not layout_validator.is_valid_layout(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_DASHBOARDS_REGEXES) or file_type == 'dashboard':
            dashboard_validator = DashboardValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                     print_as_warnings=self.print_ignored_errors)
            if not dashboard_validator.is_valid_dashboard(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_INCIDENT_TYPES_REGEXES) or file_type == 'incidenttype':
            incident_type_validator = IncidentTypeValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                            print_as_warnings=self.print_ignored_errors)
            if not incident_type_validator.is_valid_incident_type(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_MAPPER_REGEXES) or file_type == 'mapper':
            mapper_validator = MapperValidator(structure_validator, ignored_errors=ignored_errors_list,
                                               print_as_warnings=self.print_ignored_errors)
            if not mapper_validator.is_valid_mapper(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES) or file_type == 'classifier':
            classifier_validator = ClassifierValidator(structure_validator, ignored_errors=ignored_errors_list,
                                                       print_as_warnings=self.print_ignored_errors)
            if not classifier_validator.is_valid_classifier(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, JSON_ALL_CLASSIFIER_REGEXES_5_9_9) or file_type == 'classifier_5_9_9':
            classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=False,
                                                       ignored_errors=ignored_errors_list,
                                                       print_as_warnings=self.print_ignored_errors)
            if not classifier_validator.is_valid_classifier(validate_rn=False):
                self._is_valid = False

        elif checked_type(file_path, CHECKED_TYPES_REGEXES):
            print(f'Could not find validations for file {file_path}')

        else:
            error_message, error_code = Errors.file_type_not_supported()
            if self.handle_error(error_message, error_code, file_path=file_path):
                self._is_valid = False

    def validate_all_files(self, skip_conf_json):
        print('\nValidating all files')

        if not skip_conf_json:
            print('Validating conf.json')
            conf_json_validator = ConfJsonValidator()
            if not conf_json_validator.is_valid_conf_json():
                self._is_valid = False

        packs = {os.path.basename(pack) for pack in glob(f'{PACKS_DIR}/*')}
        self.validate_pack_unique_files(packs)
        all_files_to_validate = set()

        # go over packs
        for pack_name in os.listdir(PACKS_DIR):
            pack_path = os.path.join(PACKS_DIR, pack_name)

            for dir_name in os.listdir(pack_path):
                dir_path = os.path.join(pack_path, dir_name)

                if dir_name not in CONTENT_ENTITIES_DIRS:
                    continue

                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)

                    if os.path.isfile(file_path):
                        is_yml_file = file_path.endswith('.yml') and \
                            dir_name in (constants.INTEGRATIONS_DIR, constants.SCRIPTS_DIR, constants.PLAYBOOKS_DIR)

                        is_json_file = file_path.endswith('.json') and \
                            dir_name not in (constants.INTEGRATIONS_DIR, constants.SCRIPTS_DIR, constants.PLAYBOOKS_DIR)

                        is_md_file = file_path.endswith('.md') and 'CHANGELOG' not in file_path

                        if is_yml_file or is_json_file or is_md_file:
                            all_files_to_validate.add(file_path)

                    else:
                        inner_dir_path = file_path
                        for inner_file_name in os.listdir(inner_dir_path):
                            inner_file_path = os.path.join(inner_dir_path, inner_file_name)

                            if os.path.isfile(inner_file_path):
                                is_yml_file = inner_file_path.endswith('.yml') and \
                                    (f'/{constants.INTEGRATIONS_DIR}/' in inner_file_path or
                                     f'/{constants.SCRIPTS_DIR}/' in inner_file_path or
                                     f'/{constants.PLAYBOOKS_DIR}/' in inner_file_path)

                                is_md_file = inner_file_path.endswith('README.md')

                                if is_yml_file or is_md_file:
                                    all_files_to_validate.add(inner_file_path)

        click.secho(f'\nValidating all {len(all_files_to_validate)} Pack and Beta Integration files\n',
                    fg="bright_cyan")
        for index, file in enumerate(sorted(all_files_to_validate)):
            click.echo(f'Validating {file}. Progress: {"{:.2f}".format(index / len(all_files_to_validate) * 100)}%')
            self.run_all_validations_on_file(file, file_type=find_type(file))

    def validate_pack(self):
        """Validate files in a specified pack"""
        print_color(f'Validating {self.file_path}', LOG_COLORS.GREEN)
        pack_files = {file for file in glob(fr'{self.file_path}/**', recursive=True) if
                      not should_file_skip_validation(file)}
        self.validate_pack_unique_files(glob(fr'{os.path.abspath(self.file_path)}'))
        for file in pack_files:
            click.echo(f'Validating {file}')
            self.run_all_validations_on_file(file, file_type=find_type(file))

    def validate_all_files_schema(self):
        """Validate all files in the repo are in the right format."""
        # go over packs
        for pack_name in os.listdir(PACKS_DIR):
            pack_path = os.path.join(PACKS_DIR, pack_name)
            ignore_errors_list = self.get_error_ignore_list(pack_name)

            for dir_name in os.listdir(pack_path):
                dir_path = os.path.join(pack_path, dir_name)

                if dir_name not in CONTENT_ENTITIES_DIRS or \
                        dir_name in [constants.REPORTS_DIR, constants.DASHBOARDS_DIR]:
                    continue

                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)

                    if os.path.isfile(file_path):
                        is_yml_file = file_path.endswith('.yml') and \
                            dir_name in (constants.INTEGRATIONS_DIR, constants.SCRIPTS_DIR, constants.PLAYBOOKS_DIR)

                        is_json_file = file_path.endswith('.json') and \
                            dir_name not in (
                            constants.INTEGRATIONS_DIR, constants.SCRIPTS_DIR, constants.PLAYBOOKS_DIR)

                        if is_yml_file or is_json_file:
                            print("Validating {}".format(file_path))
                            self.is_backward_check = False  # if not using git, no need for BC checks
                            structure_validator = StructureValidator(file_path, ignored_errors=ignore_errors_list,
                                                                     print_as_warnings=self.print_ignored_errors)
                            if not structure_validator.is_valid_scheme():
                                self._is_valid = False

                    else:
                        inner_dir_path = file_path
                        for inner_file_name in os.listdir(inner_dir_path):
                            inner_file_path = os.path.join(inner_dir_path, inner_file_name)

                            if os.path.isfile(inner_file_path):
                                is_yml_file = inner_file_path.endswith('.yml') and \
                                    (f'/{constants.INTEGRATIONS_DIR}/' in inner_file_path or
                                     f'/{constants.SCRIPTS_DIR}/' in inner_file_path or
                                     f'/{constants.PLAYBOOKS_DIR}/' in inner_file_path)

                                if is_yml_file:
                                    print("Validating {}".format(inner_file_path))
                                    self.is_backward_check = False  # if not using git, no need for BC checks
                                    structure_validator = StructureValidator(inner_file_path,
                                                                             ignored_errors=ignore_errors_list,
                                                                             print_as_warnings=self.print_ignored_errors)
                                    if not structure_validator.is_valid_scheme():
                                        self._is_valid = False

    def is_valid_structure(self):
        """Check if the structure is valid for the case we are in, master - all files, branch - changed files.

        Returns:
            (bool). Whether the structure is valid or not.
        """
        if self.validate_all:
            self.validate_all_files(self.skip_conf_json)
            return self._is_valid

        if not self.skip_conf_json:
            if not self.conf_json_validator.is_valid_conf_json():
                self._is_valid = False

        if self.use_git:
            if self.branch_name != 'master' and (not self.branch_name.startswith('19.') and
                                                 not self.branch_name.startswith('20.')):
                if not self.is_circle:
                    print('Validating both committed and non-committed changed files')
                else:
                    print('Validating committed changed files only')
                self.validate_committed_files()
            else:
                self.validate_against_previous_version(no_error=True)
                click.secho('\nValidates all of Content repo directories according to their schemas\n', fg='bright_cyan')
                self.validate_all_files_schema()

        else:
            if self.file_path:
                if os.path.isfile(self.file_path):
                    print('Not using git, validating file: {}'.format(self.file_path))
                    self.is_backward_check = False  # if not using git, no need for BC checks
                    self.validate_added_files({self.file_path}, file_type=find_type(self.file_path))
                elif os.path.isdir(self.file_path):
                    self.validate_pack()
            else:
                print('Not using git, validating all files.')
                self.validate_all_files_schema()

        return self._is_valid

    def validate_against_previous_version(self, no_error=False):
        """Validate all files that were changed between previous version and branch_sha

        Args:
            no_error (bool): If set to true will restore self._is_valid after run (will not return new errors)
        """
        if not self.prev_ver:
            content_release_branch_id = self.get_content_release_identifier()
            if not content_release_branch_id:
                print_warning('could\'t get content\'s release branch ID. Skipping validation.')
                return
            else:
                self.prev_ver = content_release_branch_id

        print_color('Starting validation against {}'.format(self.prev_ver), LOG_COLORS.GREEN)
        modified_files, _, _, _ = self.get_modified_and_added_files(self.prev_ver)
        prev_self_valid = self._is_valid
        self.validate_modified_files(modified_files, tag=self.prev_ver)
        if no_error:
            self._is_valid = prev_self_valid

    # parser.add_argument('-t', '--test-filter', type=str2bool, default=False,
    #                     help='Check that tests are valid.')
    # TODO: after validation there was a step to run the configure_tests script to check each changed file
    #  had a relevant test - was used as part of the hooks.

    @staticmethod
    def _is_py_script_or_integration(file_path):
        file_yml = get_yaml(file_path)
        if re.match(INTEGRATION_REGEX, file_path, re.IGNORECASE):
            if file_yml.get('script', {}).get('type', 'javascript') != 'python':
                return False
            return True

        if re.match(SCRIPT_REGEX, file_path, re.IGNORECASE):
            if file_yml.get('type', 'javascript') != 'python':
                return False

            return True

        return False

    def get_content_release_identifier(self):
        try:
            file_content = get_remote_file('.circleci/config.yml', tag=self.branch_name)
        except Exception:
            return
        else:
            return file_content.get('jobs').get('build').get('environment').get('GIT_SHA1')

    @staticmethod
    def get_pack_ignore_file_path(pack_name):
        return os.path.join(PACKS_DIR, pack_name, PACKS_PACK_IGNORE_FILE_NAME)

    @staticmethod
    def create_ignored_errors_list(errors_to_check):
        ignored_error_list = []
        all_errors = ERROR_CODE.values()
        for error_code in all_errors:
            error_type = error_code[:2]
            if error_code not in errors_to_check and error_type not in errors_to_check:
                ignored_error_list.append(error_code)

        return ignored_error_list

    def add_ignored_errors_to_list(self, config, section, key, ignored_errors_list):
        # For now one can only ignore BA101 error.
        if key == 'ignore' and 'BA101' in str(config[section][key]).split(','):
            ignored_errors_list.extend(['BA101'])

        if key in PRESET_ERROR_TO_IGNORE:
            ignored_errors_list.extend(PRESET_ERROR_TO_IGNORE.get(key))

        if key in PRESET_ERROR_TO_CHECK:
            ignored_errors_list.extend(
                self.create_ignored_errors_list(PRESET_ERROR_TO_CHECK.get(key)))

    def get_error_ignore_list(self, pack_name):
        ignored_errors_list = {}
        if pack_name:
            pack_ignore_path = self.get_pack_ignore_file_path(pack_name)

            if os.path.isfile(pack_ignore_path):
                try:
                    config = ConfigParser(allow_no_value=True)
                    config.read(pack_ignore_path)

                    # create file specific ignored errors list
                    for section in config.sections():
                        if section.startswith("file:"):
                            file_name = section[5:]
                            ignored_errors_list[file_name] = []
                            for key in config[section]:
                                self.add_ignored_errors_to_list(config, section, key, ignored_errors_list[file_name])

                except MissingSectionHeaderError:
                    pass

        return ignored_errors_list
