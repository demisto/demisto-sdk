import os
import re
from configparser import ConfigParser, MissingSectionHeaderError
from enum import Enum

import click
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    CODE_FILES_REGEX, CONTENT_ENTITIES_DIRS, IGNORED_TYPES_REGEXES,
    KNOWN_FILE_STATUSES, OLD_YML_FORMAT_FILE, PACKS_DIR,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_RELEASE_NOTES_REGEX, PACKS_SCRIPT_NON_SPLIT_YML_REGEX, SCHEMA_REGEX)
from demisto_sdk.commands.common.errors import (ALLOWED_IGNORE_ERRORS,
                                                ERROR_CODE,
                                                FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
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
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.common.tools import (checked_type,
                                               filter_packagify_changes,
                                               find_type, get_pack_name,
                                               get_remote_file, get_yaml,
                                               is_file_path_in_pack,
                                               run_command)


class FileType(Enum):
    integration = 1
    script = 2
    playbook = 3
    testplaybook = 4
    betaintegration = 5
    incidentfield = 6
    indicatorfield = 7
    reputation = 8
    layout = 9
    dashboard = 10
    incidenttype = 11
    mapper = 12
    classifier_5_9_9 = 13
    classifier = 14
    widget = 15
    report = 16
    connection = 17
    readme = 18
    releasenotes = 19


SKIPPED_FILE_TYPES = ('changelog', 'description', 'testplaybook')


class ValidateManager:
    def __init__(self, is_backward_check=True, prev_ver=None, use_git=False, only_committed_files=False,
                 print_ignored_files=False, skip_conf_json=True, validate_id_set=False, file_path=None,
                 validate_all=False, is_external_repo=False, skip_pack_rn_validation=False, print_ignored_errors=False,
                 silence_init_prints=True):
        self.handle_error = BaseValidator(print_as_warnings=print_ignored_errors).handle_error
        self.print_ignored_errors = print_ignored_errors
        self.skip_docker_checks = False
        self.skip_conf_json = skip_conf_json
        self.is_backward_check = is_backward_check
        self.validate_id_set = validate_id_set
        self.is_circle = only_committed_files
        self.validate_all = validate_all
        self.file_path = file_path
        self.branch_name = ''
        self.use_git = use_git
        self.skip_pack_rn_validation = skip_pack_rn_validation
        self.changes_in_schema = False
        self.check_only_schema = False
        self.prev_ver = prev_ver if prev_ver else 'origin/master'
        self.print_ignored_files = print_ignored_files
        self.added_rn = set()

        if is_external_repo:
            click.echo('Running in a private repository')
            self.skip_conf_json = True

        if validate_all:
            self.skip_docker_checks = True
            self.skip_pack_rn_validation = True

        if self.validate_id_set:
            self.id_set_validator = IDSetValidator(is_circle=self.is_circle, configuration=Configuration())

    def print_final_report(self, valid):
        if valid:
            self.print_ignored_errors_report()
            click.secho('\nThe files are valid', fg='green')
            return 0
        else:
            all_failing_files = '\n'.join(FOUND_FILES_AND_ERRORS)
            click.secho(f"\n=========== Found errors in the following files ===========\n\n{all_failing_files}\n",
                        fg="bright_red")
            self.print_ignored_errors_report()
            click.secho('The files were found as invalid, the exact error message can be located above',
                        fg='red')
            return 1

    def run_validation(self):
        """Initiates validation in accordance with mode (i,g,a)
        """
        if self.validate_all:
            return self.print_final_report(self.run_validation_on_all_packs())
        if self.file_path:
            return self.print_final_report(self.run_validation_on_specific_files())
        if self.use_git:
            return self.print_final_report(self.run_validation_using_git())

    def run_validation_on_specific_files(self):
        """Run validations only on specific files
        """
        valid_files = set()

        for path in self.file_path.split(','):
            error_ignore_list = self.get_error_ignore_list(get_pack_name(path))

            if os.path.isfile(path):
                click.secho('\n================= Validating file =================', fg="bright_cyan")
                valid_files.add(self.run_validations_on_file(path, error_ignore_list))

            else:
                path = path.rstrip('/')
                dir_name = os.path.basename(path)
                if dir_name in CONTENT_ENTITIES_DIRS:
                    click.secho(f'\n================= Validating content directory {path} =================',
                                fg="bright_cyan")
                    valid_files.add(self.run_validation_on_content_entities(path, error_ignore_list))
                else:
                    rest_of_path = path.replace(f'/{dir_name}', '')
                    if os.path.basename(rest_of_path) == PACKS_DIR:
                        click.secho(f'\n================= Validating pack {path} =================',
                                    fg="bright_cyan")
                        valid_files.add(self.run_validations_on_pack(path))

                    else:
                        click.secho(f'\n================= Validating package {path} =================',
                                    fg="bright_cyan")
                        valid_files.add(self.run_validation_on_package(path, error_ignore_list))

        return all(valid_files)

    def run_validation_on_all_packs(self):
        """Runs validations on all files in all packs in repo (a)

        Returns:
            bool. true if all files are valid, false otherwise.
        """
        click.secho('\n================= Validating all files =================', fg="bright_cyan")
        valid_repo = set()

        if not self.skip_conf_json:
            print('\nValidating conf.json')
            conf_json_validator = ConfJsonValidator()
            valid_repo.add(conf_json_validator.is_valid_conf_json())

        for pack_name in os.listdir(PACKS_DIR):
            pack_path = os.path.join(PACKS_DIR, pack_name)
            valid_repo.add(self.run_validations_on_pack(pack_path))

        return all(valid_repo)

    def run_validations_on_pack(self, pack_path):
        """Runs validation on all files in given pack. (i,g,a)

        Args:
            pack_path: the path to the pack.

        Returns:
            bool. true if all files in pack are valid, false otherwise.
        """
        valid_pack = set()
        pack_error_ignore_list = self.get_error_ignore_list(os.path.basename(pack_path))

        valid_pack.add(self.validate_pack_unique_files(pack_path, pack_error_ignore_list))

        for content_dir in os.listdir(pack_path):
            content_entity_path = os.path.join(pack_path, content_dir)
            if content_dir in CONTENT_ENTITIES_DIRS:
                valid_pack.add(self.run_validation_on_content_entities(content_entity_path, pack_error_ignore_list))

        return all(valid_pack)

    def run_validation_on_content_entities(self, content_entity_dir_path, pack_error_ignore_list):
        """Gets non-pack folder and runs validation within it (Scripts, Integrations...)

        Returns:
            bool. true if all files in directory are valid, false otherwise.
        """
        valid_directory = set()
        for file_name in os.listdir(content_entity_dir_path):
            file_path = os.path.join(content_entity_dir_path, file_name)
            if os.path.isfile(file_path):
                if file_path.endswith('.json') or file_path.endswith('.yml') or file_path.endswith('.md'):
                    valid_directory.add(self.run_validations_on_file(file_path, pack_error_ignore_list))

            else:
                valid_directory.add(self.run_validation_on_package(file_path, pack_error_ignore_list))

        return all(valid_directory)

    def run_validation_on_package(self, package_path, pack_error_ignore_list):
        valid_package = set()

        for file_name in os.listdir(package_path):
            file_path = os.path.join(package_path, file_name)
            if file_path.endswith('.yml') or file_path.endswith('.md'):
                valid_package.add(self.run_validations_on_file(file_path, pack_error_ignore_list))

        return all(valid_package)

    # flake8: noqa: C901
    def run_validations_on_file(self, file_path, pack_error_ignore_list, is_modified=False,
                                old_file_path=None, modified_files=None, added_files=None):
        """Choose a validator to run for a single file. (i)

        Args:
            modified_files: A set of modified files - used for RN validation
            added_files: A set of added files - used for RN validation
            old_file_path: The old file path for renamed files
            pack_error_ignore_list: A dictionary of all pack ignored errors
            file_path: the file on which to run.
            is_modified: whether the file is modified or added.

        Returns:
            bool. true if file is valid, false otherwise.
        """

        file_type = find_type(file_path)

        if file_type in SKIPPED_FILE_TYPES:
            return True

        elif file_type is None:
            error_message, error_code = Errors.file_type_not_supported()
            if self.handle_error(error_message=error_message, error_code=error_code, file_path=f'\n{file_path}'):
                return False

        if not self.check_only_schema:
            click.echo(f"\nValidating {file_path} as {file_type}")

        structure_validator = StructureValidator(file_path, predefined_scheme=file_type,
                                                 ignored_errors=pack_error_ignore_list,
                                                 print_as_warnings=self.print_ignored_errors, tag=self.prev_ver,
                                                 old_file_path=old_file_path)

        click.secho(f'Validating scheme for {file_path}')
        if not structure_validator.is_valid_file():
            return False

        if self.check_only_schema:
            return True

        if not self.check_for_spaces_in_file_name(file_path):
            return False

        if file_type == 'releasenotes' and not self.skip_pack_rn_validation:
            pack_name = get_pack_name(file_path)
            self.added_rn.add(pack_name)
            if not added_files:
                added_files = {file_path}

            release_notes_validator = ReleaseNotesValidator(file_path, pack_name=pack_name,
                                                            modified_files=modified_files, added_files=added_files,
                                                            ignored_errors=pack_error_ignore_list,
                                                            print_as_warnings=self.print_ignored_errors)
            return release_notes_validator.is_file_valid()

        if file_type == 'readme':
            readme_validator = ReadMeValidator(file_path, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors)
            return readme_validator.is_valid_file()

        if self.validate_id_set:
            click.echo(f"Validating id set registration for {file_path}")
            if not self.id_set_validator.is_file_valid_in_set(file_path):
                return False

        # No validators for reports not connections
        if file_type in {'report', 'canvas-context-connections'}:
            return True

        elif file_type == 'playbook':
            playbook_validator = PlaybookValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                   print_as_warnings=self.print_ignored_errors)
            return playbook_validator.is_valid_playbook(validate_rn=False)

        elif file_type == 'integration':
            integration_validator = IntegrationValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                         print_as_warnings=self.print_ignored_errors,
                                                         skip_docker_check=self.skip_docker_checks)
            if is_modified and self.is_backward_check:
                return all([integration_validator.is_valid_file(validate_rn=False, skip_test_conf=self.skip_conf_json),
                            integration_validator.is_backward_compatible()])
            else:
                return integration_validator.is_valid_file(validate_rn=False, skip_test_conf=self.skip_conf_json)

        elif file_type == 'script':
            script_validator = ScriptValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors,
                                               skip_docker_check=self.skip_docker_checks)
            if is_modified and self.is_backward_check:
                return all([script_validator.is_valid_file(validate_rn=False),
                            script_validator.is_backward_compatible()])
            else:
                return script_validator.is_valid_file(validate_rn=False)

        elif file_type == 'betaintegration':
            integration_validator = IntegrationValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                         print_as_warnings=self.print_ignored_errors,
                                                         skip_docker_check=self.skip_docker_checks)
            return integration_validator.is_valid_beta_integration()

        elif file_type == 'image':
            image_validator = ImageValidator(file_path, ignored_errors=pack_error_ignore_list)
            return image_validator.is_valid()

        # incident fields and indicator fields are using the same scheme.
        elif file_type in ('incidentfield', 'indicatorfield'):
            incident_field_validator = IncidentFieldValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                              print_as_warnings=self.print_ignored_errors)
            if is_modified and self.is_backward_check:
                return all([incident_field_validator.is_valid_file(validate_rn=False),
                            incident_field_validator.is_backward_compatible()])
            else:
                return incident_field_validator.is_valid_file(validate_rn=False)

        elif file_type == 'reputation':
            reputation_validator = ReputationValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                       print_as_warnings=self.print_ignored_errors)
            return reputation_validator.is_valid_file(validate_rn=False)

        elif file_type == 'layout':
            layout_validator = LayoutValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors)
            return layout_validator.is_valid_layout(validate_rn=False)

        elif file_type == 'dashboard':
            dashboard_validator = DashboardValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                     print_as_warnings=self.print_ignored_errors)
            return dashboard_validator.is_valid_dashboard(validate_rn=False)

        elif file_type == 'incidenttype':
            incident_type_validator = IncidentTypeValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                            print_as_warnings=self.print_ignored_errors)
            if is_modified and self.is_backward_check:
                return all([incident_type_validator.is_valid_incident_type(validate_rn=False),
                            incident_type_validator.is_backward_compatible()])
            else:
                return incident_type_validator.is_valid_incident_type(validate_rn=False)

        elif file_type == 'mapper':
            mapper_validator = MapperValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors)
            return mapper_validator.is_valid_mapper(validate_rn=False)

        elif file_type == 'classifier_5_9_9':
            classifier_validator = ClassifierValidator(structure_validator, new_classifier_version=False,
                                                       ignored_errors=pack_error_ignore_list,
                                                       print_as_warnings=self.print_ignored_errors)
            return classifier_validator.is_valid_classifier(validate_rn=False)

        elif file_type == 'classifier':
            classifier_validator = ClassifierValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                                       print_as_warnings=self.print_ignored_errors)
            return classifier_validator.is_valid_classifier(validate_rn=False)

        elif file_type == 'widget':
            widget_validator = WidgetValidator(structure_validator, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors)
            return widget_validator.is_valid_file(validate_rn=False)

        else:
            error_message, error_code = Errors.file_type_not_supported()
            if self.handle_error(error_message=error_message, error_code=error_code, file_path=file_path):
                return False

        return True

    def run_validation_using_git(self):
        """Runs validation on only changed packs/files (g)
        """
        self.branch_name = self.get_current_working_branch()
        if self.branch_name != 'master' and (not self.branch_name.startswith('19.') and
                                             not self.branch_name.startswith('20.')):
            compare_type = '.'
            self.prev_ver = 'origin/master'

        else:
            self.skip_pack_rn_validation = True
            compare_type = ''
            self.prev_ver = self.get_content_release_identifier()

        click.secho(f'\n================= Running validation on branch {self.branch_name} =================',
                    fg="bright_cyan")

        click.echo(f"Validating against {self.prev_ver}")

        modified_files, added_files, old_format_files = self.get_modified_and_added_files(compare_type, self.prev_ver)

        valid_files = set()

        click.secho(f'\n================= Running validation on modified files =================',
                    fg="bright_cyan")
        for file_path in modified_files:
            # handle renamed files
            if isinstance(file_path, tuple):
                old_file_path = file_path[0]
                file_path = file_path[1]

            else:
                old_file_path = None

            pack_name = get_pack_name(file_path)
            valid_files.add(self.run_validations_on_file(file_path, self.get_error_ignore_list(pack_name),
                                                         is_modified=True, old_file_path=old_file_path))

        click.secho(f'\n================= Running validation on newly added files =================',
                    fg="bright_cyan")

        for file_path in added_files:
            pack_name = get_pack_name(file_path)
            valid_files.add(self.run_validations_on_file(file_path, self.get_error_ignore_list(pack_name),
                                                         is_modified=False, modified_files=modified_files,
                                                         added_files=added_files))
        if not self.skip_pack_rn_validation:
            click.secho(f'\n================= Verifying no duplicated release notes =================',
                        fg="bright_cyan")

            valid_files.add(self.verify_no_dup_rn(added_files))

            click.secho("\n================= Checking for missing release notes =================\n", fg="bright_cyan")

            valid_files.add(self.verify_no_missing_rn(self.get_changed_packs(modified_files)))

        if old_format_files:
            click.secho(f'\n================= Running validation on old format files =================',
                        fg="bright_cyan")
            valid_files.add(self.validate_no_old_format(old_format_files))

        if self.changes_in_schema:
            self.check_only_schema = True
            click.secho(f'\n================= Detected changes in schema - Running validation on all files '
                        f'=================',
                        fg="bright_cyan")
            valid_files.add(self.run_validation_on_all_packs())

        return all(valid_files)

    """ ######################################## Unique Validations ####################################### """

    def validate_pack_unique_files(self, pack_path: str, pack_error_ignore_list: dict) -> bool:
        """
        Runs validations on the following pack files:
        * .secret-ignore: Validates that the file exist and that the file's secrets can be parsed as a list delimited by '\n'
        * .pack-ignore: Validates that the file exists and that all regexes in it can be compiled
        * README.md file: Validates that the file exists
        * pack_metadata.json: Validates that the file exists and that it has a valid structure
        Args:
            pack_error_ignore_list: A dictionary of all pack ignored errors
            pack_path: A path to a pack
        """
        print(f'\nValidating {pack_path} unique pack files')

        pack_unique_files_validator = PackUniqueFilesValidator(os.path.basename(pack_path),
                                                               ignored_errors=pack_error_ignore_list,
                                                               print_as_warnings=self.print_ignored_errors)
        pack_errors = pack_unique_files_validator.validate_pack_unique_files()
        if pack_errors:
            click.secho(pack_errors, fg="bright_red")
            return False

        return True

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
                return False
        return True

    def verify_no_dup_rn(self, added_files):
        """Validated that among the added files - there are no duplicated RN for the same pack.

        Args:
            added_files(set): The added files

        Returns:
            bool. True if no duplications found, false otherwise
        """
        added_rn = set()
        for file in added_files:
            if re.search(PACKS_RELEASE_NOTES_REGEX, file):
                pack_name = get_pack_name(file)
                if pack_name not in added_rn:
                    added_rn.add(pack_name)
                else:
                    error_message, error_code = Errors.multiple_release_notes_files()
                    if self.handle_error(error_message, error_code, file_path=pack_name):
                        return False

        click.secho("No duplicated release notes found.\n", fg="bright_green")
        return True

    def verify_no_missing_rn(self, changed_packs):
        """Validate that there are no missing RN for changed files

        Args:
            changed_packs set: a set of modified files without any readme/release-notes files.

        Returns:
            bool. True if no missing RN found, False otherwise
        """
        if self.skip_pack_rn_validation is False:
            missing_rn = changed_packs.difference(self.added_rn)

            if len(missing_rn) > 0:
                is_valid = set()
                for pack in missing_rn:
                    # # ignore RN in NonSupported pack
                    if 'NonSupported' in pack:
                        continue
                    ignored_errors_list = self.get_error_ignore_list(pack)
                    error_message, error_code = Errors.missing_release_notes_for_pack(pack)
                    if not BaseValidator(ignored_errors=ignored_errors_list,
                                         print_as_warnings=self.print_ignored_errors).handle_error(
                            error_message, error_code, file_path=os.path.join(PACKS_DIR, pack)):
                        is_valid.add(True)

                    else:
                        is_valid.add(False)

                return all(is_valid)

            else:
                click.secho("No missing release notes found.\n", fg="bright_green")
                return True

    """ ######################################## Git Tools and filtering ####################################### """

    def get_modified_and_added_files(self, compare_type, prev_ver):
        """Get the modified and added files from a specific branch

        Args:
            compare_type (str): whether to run diff with two dots (..) or three (...)
            prev_ver (str): Against which branch to run the comparision - master/last releaese

        Returns:
            tuple. 3 sets representing modified files, added files and files of old format who have changed.
        """
        click.echo("Collecting all committed files")
        # all committed changes of the current branch vs the prev_ver
        all_committed_files_string = run_command(
            f'git diff --name-status {prev_ver}..{compare_type}refs/heads/{self.branch_name}')

        modified_files, added_files, _, old_format_files = self.filter_changed_files(all_committed_files_string,
                                                                                     prev_ver)
        if not self.is_circle:
            click.echo("Collecting all local changed files")
            # all local non-committed changes and changes against prev_ver
            all_changed_files_string = run_command('git diff --name-status {}'.format(prev_ver))
            modified_files_from_tag, added_files_from_tag, _, _ = \
                self.filter_changed_files(all_changed_files_string, print_ignored_files=self.print_ignored_files)

            # only changes against prev_ver (without local changes)
            outer_changes_files_string = run_command('git diff --name-status --no-merges HEAD')
            nc_modified_files, nc_added_files, nc_deleted_files, nc_old_format_files = self.filter_changed_files(
                outer_changes_files_string, print_ignored_files=self.print_ignored_files)

            old_format_files = old_format_files.union(nc_old_format_files)
            modified_files = modified_files.union(
                modified_files_from_tag.intersection(nc_modified_files))

            added_files = added_files.union(
                added_files_from_tag.intersection(nc_added_files))

            modified_files = modified_files - set(nc_deleted_files)
            added_files = added_files - set(nc_modified_files) - set(nc_deleted_files)

        return modified_files, added_files, old_format_files

    def filter_changed_files(self, files_string, tag='master', print_ignored_files=False):
        """Get lists of the modified files in your branch according to the files string.

        Args:
            files_string (string): String that was calculated by git using `git diff` command.
            tag (string): String of git tag used to update modified files.
            print_ignored_files (bool): should print ignored files.

        Returns:
            Tuple of sets.
        """
        all_files = files_string.split('\n')
        deleted_files = set()
        added_files_list = set()
        modified_files_list = set()
        old_format_files = set()
        for f in all_files:
            file_data = list(filter(None, f.split('\t')))
            if not file_data:
                continue

            file_status = file_data[0]
            file_path = file_data[1]

            if file_status.lower().startswith('r'):
                file_status = 'r'
                file_path = file_data[2]

            # if the file is a code file - change path to the associated yml path.
            if checked_type(file_path, CODE_FILES_REGEX) and file_status.lower() != 'd' \
                    and not (file_path.endswith('_test.py') or file_path.endswith('.Tests.ps1')):
                # naming convention - code file and yml file in packages must have same name.
                file_path = os.path.splitext(file_path)[0] + '.yml'

            # ignore changes in JS files and unit test files.
            elif file_path.endswith('.js') or file_path.endswith('.py') or file_path.endswith('.ps1'):
                continue

            # identify deleted files
            if file_status.lower() == 'd' and checked_type(file_path) and not file_path.startswith('.'):
                deleted_files.add(file_path)

            # ignore directories
            elif not os.path.isfile(file_path):
                continue

            # changes in old scripts and integrations
            elif file_status.lower() in ['m', 'a', 'r'] and checked_type(file_path, OLD_YML_FORMAT_FILE) and \
                    self._is_py_script_or_integration(file_path):
                old_format_files.add(file_path)

            # identify modified files
            elif file_status.lower() == 'm' and checked_type(file_path) and not file_path.startswith('.'):
                modified_files_list.add(file_path)

            # identify added files
            elif file_status.lower() == 'a' and checked_type(file_path) and not file_path.startswith('.'):
                added_files_list.add(file_path)

            # identify renamed files
            elif file_status.lower().startswith('r') and checked_type(file_path):
                # if a code file changed, take the associated yml file.
                if checked_type(file_data[2], CODE_FILES_REGEX):
                    modified_files_list.add(file_path)

                else:
                    # file_data[1] = old name, file_data[2] = new name
                    modified_files_list.add((file_data[1], file_data[2]))

            # detect changes in schema
            elif checked_type(file_path, [SCHEMA_REGEX]):
                modified_files_list.add(file_path)
                self.changes_in_schema = True

            elif file_status.lower() not in KNOWN_FILE_STATUSES:
                click.secho('{} file status is an unknown one, please check. File status was: {}'
                            .format(file_path, file_status), fg="bright_red")

            elif print_ignored_files and not checked_type(file_path, IGNORED_TYPES_REGEXES):
                click.secho('Ignoring file path: {}'.format(file_path), fg="yellow")

        modified_files_list, added_files_list, deleted_files = filter_packagify_changes(
            modified_files_list,
            added_files_list,
            deleted_files,
            tag)

        return modified_files_list, added_files_list, deleted_files, old_format_files

    """ ######################################## Validate Tools ############################################### """

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

    @staticmethod
    def get_allowed_ignored_errors_from_list(error_list):
        allowed_ignore_list = []
        for error in error_list:
            if error in ALLOWED_IGNORE_ERRORS:
                allowed_ignore_list.append(error)

        return allowed_ignore_list

    def add_ignored_errors_to_list(self, config, section, key, ignored_errors_list):
        if key == 'ignore':
            ignored_errors_list.extend(self.get_allowed_ignored_errors_from_list(str(config[section][key]).split(',')))

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

    def check_for_spaces_in_file_name(self, file_path):
        file_name = os.path.basename(file_path)
        if file_name.count(' ') > 0:
            error_message, error_code = Errors.file_name_include_spaces_error(file_name)
            if self.handle_error(error_message, error_code, file_path):
                return False

        return True

    @staticmethod
    def get_current_working_branch():
        branches = run_command('git branch')
        branch_name_reg = re.search(r'\* (.*)', branches)
        return branch_name_reg.group(1)

    def get_content_release_identifier(self):
        try:
            file_content = get_remote_file('.circleci/config.yml', tag=self.branch_name)
        except Exception:
            return
        else:
            return file_content.get('jobs').get('build').get('environment').get('GIT_SHA1')

    @staticmethod
    def _is_py_script_or_integration(file_path):
        file_yml = get_yaml(file_path)
        if re.match(PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):
            if file_yml.get('script', {}).get('type', 'javascript') != 'python':
                return False
            return True

        if re.match(PACKS_SCRIPT_NON_SPLIT_YML_REGEX, file_path, re.IGNORECASE):
            if file_yml.get('type', 'javascript') != 'python':
                return False

            return True

        return False

    @staticmethod
    def get_changed_packs(modified_files):
        packs = set()
        for changed_file in modified_files:
            if isinstance(changed_file, tuple):
                changed_file = changed_file[1]
            if 'ReleaseNotes' not in changed_file and "README" not in changed_file:
                pack = get_pack_name(changed_file)
                if pack and is_file_path_in_pack(changed_file):
                    packs.add(pack)

        return packs

    def print_ignored_errors_report(self):
        if self.print_ignored_errors:
            all_ignored_errors = '\n'.join(FOUND_FILES_AND_IGNORED_ERRORS)
            click.secho(f"\n=========== Found ignored errors in the following files ===========\n\n{all_ignored_errors}",
                        fg="yellow")
