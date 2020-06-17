import os
from configparser import ConfigParser, MissingSectionHeaderError
from enum import Enum

import click
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (CONTENT_ENTITIES_DIRS,
                                                   PACKS_DIR,
                                                   PACKS_PACK_IGNORE_FILE_NAME)
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
from demisto_sdk.commands.common.hook_validations.reputation import \
    ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.common.tools import find_type, get_pack_name


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


SKIPPED_FILE_TYPES = ('releasenotes', 'changelog', 'description', 'testplaybook')


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

        if validate_all:
            self.skip_docker_checks = True

        if self.validate_id_set:
            self.id_set_validator = IDSetValidator(is_circle=self.is_circle, configuration=Configuration())

    def print_conclusion(self, valid):
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
            return self.print_conclusion(self.run_validation_on_all_packs())
        if self.file_path:
            return self.print_conclusion(self.run_validation_on_specific_files())

    def run_validation_on_specific_files(self):
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

    def validate_against_previous_version(self):
        """Runs validation on only changed packs/files (g)

        Returns:

        """
        pass

    def get_added_and_modified_files(self):
        """Find all the changed files.

        Returns:
            tuple[list, list, list] - a list of modified, added and ignored files.
        """
        pass

    def run_validations_on_file(self, file_path, pack_error_ignore_list, is_modified=False):
        """Choose a validator to run for a single file. (i)

        Args:
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

        click.echo(f"\nValidating {file_path} as a {file_type} file")

        if not self.check_for_spaces_in_file_name(file_path):
            return False

        if file_type == 'readme':
            readme_validator = ReadMeValidator(file_path, ignored_errors=pack_error_ignore_list,
                                               print_as_warnings=self.print_ignored_errors)
            return readme_validator.is_valid_file()

        # elif file_type == 'releasenotes':
        #     release_notes_validator = ReleaseNotesValidator(file_path, pack_name=pack_name,
        #                                                     modified_files=modified_files, added_files=added_files,
        #                                                     ignored_errors=pack_error_ignore_list,
        #                                                     print_as_warnings=self.print_ignored_errors)
        #     return release_notes_validator.is_file_valid()
        #
        structure_validator = StructureValidator(file_path, predefined_scheme=file_type,
                                                 ignored_errors=pack_error_ignore_list,
                                                 print_as_warnings=self.print_ignored_errors)

        click.secho(f'Validating scheme for {file_path}')
        if not structure_validator.is_valid_file():
            return False

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

    def run_validation_on_package(self, package_path, pack_error_ignore_list):
        valid_package = set()

        for file_name in os.listdir(package_path):
            file_path = os.path.join(package_path, file_name)
            if file_path.endswith('.yml') or file_path.endswith('.md'):
                valid_package.add(self.run_validations_on_file(file_path, pack_error_ignore_list))

        return all(valid_package)

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

    def print_ignored_errors_report(self):
        if self.print_ignored_errors:
            all_ignored_errors = '\n'.join(FOUND_FILES_AND_IGNORED_ERRORS)
            click.secho(f"\n=========== Found ignored errors in the following files ===========\n\n{all_ignored_errors}",
                        fg="yellow")
