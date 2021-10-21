import os
import re
from typing import Dict, Optional

import yaml

from demisto_sdk.commands.common.constants import (
    BANG_COMMAND_ARGS_MAPPING_DICT, BANG_COMMAND_NAMES, DBOT_SCORES_DICT,
    DEPRECATED_REGEXES, ENDPOINT_COMMAND_NAME, ENDPOINT_FLEXIBLE_REQUIRED_ARGS,
    FEED_REQUIRED_PARAMS, FETCH_REQUIRED_PARAMS, FIRST_FETCH,
    FIRST_FETCH_PARAM, INTEGRATION_CATEGORIES, IOC_OUTPUTS_DICT, MAX_FETCH,
    MAX_FETCH_PARAM, PYTHON_SUBTYPES, REPUTATION_COMMAND_NAMES, TYPE_PWSH,
    XSOAR_CONTEXT_STANDARD_URL)
from demisto_sdk.commands.common.default_additional_info_loader import \
    load_default_additional_info_dict
from demisto_sdk.commands.common.errors import (FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
                                                Errors)
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.description import \
    DescriptionValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.tools import (
    _get_file_id, compare_context_path_in_yml_and_readme, get_core_pack_list,
    get_file_version_suffix_if_exists, get_files_in_dir, get_pack_name,
    is_iron_bank_pack, print_error, server_version_compare)

default_additional_info = load_default_additional_info_dict()


class IntegrationValidator(ContentEntityValidator):
    """IntegrationValidator is designed to validate the correctness of the file structure we enter to content repo. And
    also try to catch possible Backward compatibility breaks due to the preformed changes.
    """

    EXPIRATION_FIELD_TYPE = 17
    ALLOWED_HIDDEN_PARAMS = {'longRunning', 'feedIncremental', 'feedReputation'}

    def is_valid_version(self):
        # type: () -> bool
        if self.current_file.get("commonfields", {}).get('version') == self.DEFAULT_VERSION:
            return True

        error_message, error_code = Errors.wrong_version()
        if self.handle_error(error_message, error_code, file_path=self.file_path,
                             suggested_fix=Errors.suggest_fix(self.file_path)):
            self.is_valid = False
            return False

        return True

    def is_backward_compatible(self):
        # type: () -> bool
        """Check whether the Integration is backward compatible or not, update the _is_valid field to determine that"""
        if not self.old_file:
            return True

        answers = [
            self.is_changed_context_path(),
            self.is_removed_integration_parameters(),
            self.is_added_required_fields(),
            self.is_changed_command_name_or_arg(),
            self.is_changed_subtype(),
            self.is_not_valid_display_configuration(),
            self.is_changed_removed_yml_fields(),
            # will move to is_valid_integration after https://github.com/demisto/etc/issues/17949
            not self.is_outputs_for_reputations_commands_valid(),
        ]
        return not any(answers)

    def core_integration_validations(self, validate_rn: bool = True):
        """Perform the core integration validations (common to both beta and regular integrations)
        Args:
            validate_rn (bool): Whether to validate release notes (changelog) or not.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_subtype(),
            self.is_valid_default_array_argument_in_reputation_command(),
            self.is_valid_default_argument(),
            self.is_proxy_configured_correctly(),
            self.is_insecure_configured_correctly(),
            self.is_checkbox_param_configured_correctly(),
            self.is_valid_category(),
            self.is_id_equals_name(),
            self.is_docker_image_valid(),
            self.is_valid_feed(),
            self.is_valid_fetch(),
            self.is_there_a_runnable(),
            self.is_valid_display_name(),
            self.is_valid_pwsh(),
            self.is_valid_image(),
            self.is_valid_max_fetch_and_first_fetch(),
            self.is_valid_as_deprecated(),
            self.is_valid_parameters_display_name(),
            self.is_mapping_fields_command_exist(),
            self.is_valid_integration_file_path(),
            self.has_no_duplicate_params(),
            self.has_no_duplicate_args(),
            self.is_there_separators_in_names(),
            self.name_not_contain_the_type(),
            self.is_valid_endpoint_command(),
            self.is_api_token_in_credential_type(),
        ]

        return all(answers)

    def is_valid_file(self, validate_rn: bool = True, skip_test_conf: bool = False,
                      check_is_unskipped: bool = True, conf_json_data: dict = {}) -> bool:
        """Check whether the Integration is valid or not according to the LEVEL SUPPORT OPTIONS
        that depends on the contributor type

            Args:
                validate_rn (bool): Whether to validate release notes (changelog) or not.
                skip_test_conf (bool): If true then will skip test playbook configuration validation
                check_is_unskipped (bool): Whether to check if the integration is unskipped.
                conf_file (dict):

            Returns:
                bool: True if integration is valid, False otherwise.
        """

        answers = [
            self.core_integration_validations(validate_rn),
            self.is_valid_hidden_params(),
            self.is_valid_description(beta_integration=False),
            self.is_context_correct_in_readme(),
        ]

        if check_is_unskipped:
            answers.append(self.is_unskipped_integration(conf_json_data))

        if not skip_test_conf:
            answers.append(self.are_tests_configured())

        core_packs_list = get_core_pack_list()

        pack = get_pack_name(self.file_path)
        is_core = True if pack in core_packs_list else False
        if is_core:
            answers.append(self.no_incident_in_core_packs())

        return all(answers)

    def is_valid_beta_integration(self, validate_rn: bool = True) -> bool:
        """Check whether the beta Integration is valid or not, update the _is_valid field to determine that
            Args:
                validate_rn (bool): Whether to validate release notes (changelog) or not.

            Returns:
                bool: True if integration is valid, False otherwise.
        """
        answers = [
            self.core_integration_validations(validate_rn),
            self.is_valid_beta(),
            self.is_valid_description(beta_integration=True),
        ]
        return all(answers)

    def is_valid_as_deprecated(self):
        """Check if the integration is valid as a deprecated integration."""
        answers = [
            self._is_valid_deprecated_integration_display_name(),
            self._is_valid_deprecated_integration_description(),
        ]
        return all(answers)

    def is_unskipped_integration(self, conf_json_data):
        """Validated the integration testing is not skipped."""
        skipped_integrations = conf_json_data.get('skipped_integrations', {})
        integration_id = _get_file_id('integration', self.current_file)
        if skipped_integrations and integration_id in skipped_integrations:
            skip_comment = skipped_integrations[integration_id]
            error_message, error_code = Errors.integration_is_skipped(integration_id, skip_comment)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
        return self.is_valid

    def _is_valid_deprecated_integration_display_name(self) -> bool:
        is_valid = True
        is_deprecated = self.current_file.get('deprecated', False)
        display_name = self.current_file.get('display', '')
        if is_deprecated:
            if not display_name.endswith('(Deprecated)'):
                error_message, error_code = Errors.invalid_deprecated_integration_display_name()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False
        return is_valid

    def _is_valid_deprecated_integration_description(self) -> bool:
        is_valid = True
        is_deprecated = self.current_file.get('deprecated', False)
        description = self.current_file.get('description', '')
        deprecated_v2_regex = DEPRECATED_REGEXES[0]
        deprecated_no_replace_regex = DEPRECATED_REGEXES[1]
        if is_deprecated:
            if re.search(deprecated_v2_regex, description) or re.search(deprecated_no_replace_regex, description):
                pass
            else:
                error_message, error_code = Errors.invalid_deprecated_integration_description()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False

        return is_valid

    def are_tests_configured(self) -> bool:
        """
        Checks if the integration has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        tests = self.current_file.get('tests', [])
        return self.are_tests_registered_in_conf_json_file_or_yml_file(tests)

    def is_valid_param(self, param_name, param_display):
        # type: (str, str) -> bool
        """Check if the given parameter has the right configuration."""
        err_msgs = []
        configuration = self.current_file.get('configuration', [])
        for configuration_param in configuration:
            configuration_param_name = configuration_param['name']
            if configuration_param_name == param_name:
                if configuration_param['display'] != param_display:
                    error_message, error_code = Errors.wrong_display_name(param_name, param_display)
                    formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                          should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('defaultvalue', '') not in (False, 'false', ''):
                    error_message, error_code = Errors.wrong_default_parameter_not_empty(param_name, "''")
                    formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                          should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('required', False):
                    error_message, error_code = Errors.wrong_required_value(param_name)
                    formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                          should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('type') != 8:
                    error_message, error_code = Errors.wrong_required_type(param_name)
                    formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                          should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

        if err_msgs:
            print_error('{} Received the following error for {} validation:\n{}\n {}\n'
                        .format(self.file_path, param_name, '\n'.join(err_msgs),
                                Errors.suggest_fix(file_path=self.file_path)))
            self.is_valid = False
            return False
        return True

    def is_proxy_configured_correctly(self):
        # type: () -> bool
        """Check that if an integration has a proxy parameter that it is configured properly."""
        return self.is_valid_param('proxy', 'Use system proxy settings')

    def is_insecure_configured_correctly(self):
        # type: () -> bool
        """Check that if an integration has an insecure parameter that it is configured properly."""
        insecure_field_name = ''
        configuration = self.current_file.get('configuration', [])
        for configuration_param in configuration:
            if configuration_param['name'] in ('insecure', 'unsecure'):
                insecure_field_name = configuration_param['name']
        if insecure_field_name:
            return self.is_valid_param(insecure_field_name, 'Trust any certificate (not secure)')
        return True

    def is_checkbox_param_configured_correctly(self):
        # type: () -> bool
        """Check that if an integration has a checkbox parameter it is configured properly.
        Returns:
            bool. True if the checkbox parameter is configured correctly, False otherwise.
        """
        configuration = self.current_file.get('configuration', [])
        for configuration_param in configuration:
            param_name = configuration_param['name']
            if configuration_param['type'] == 8 and param_name not in ('insecure', 'unsecure', 'proxy', 'isFetch'):
                if not self.is_valid_checkbox_param(configuration_param, param_name):
                    self.is_valid = False
        if not self.is_valid:
            return False
        return True

    def is_valid_checkbox_param(self, configuration_param, param_name):
        # type: (dict, str) -> bool
        """Check if the given checkbox parameter required field is False.
        Returns:
            bool. True if valid, False otherwise.
        """
        if configuration_param.get('required', False):
            error_message, error_code = Errors.wrong_required_value(param_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_category(self):
        # type: () -> bool
        """Check that the integration category is in the schema."""
        category = self.current_file.get('category', None)
        if category not in INTEGRATION_CATEGORIES:
            error_message, error_code = Errors.wrong_category(category)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_valid_default_array_argument_in_reputation_command(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url/cve)
            has a default non required argument and make sure the default value can accept array of inputs.

        Returns:
            bool. Whether a reputation command hold a valid argument which support array.
        """
        commands = self.current_file.get('script', {}).get('commands', [])
        if commands is None:
            commands = []
        flag = True
        for command in commands:
            command_name = command.get('name', '')
            if command_name in BANG_COMMAND_NAMES:
                command_mapping = BANG_COMMAND_ARGS_MAPPING_DICT[command_name]
                flag_found_arg = False
                for arg in command.get('arguments', []):
                    arg_name = arg.get('name')
                    if arg_name in command_mapping['default']:
                        flag_found_arg = True
                        if arg.get('default') is False:
                            error_message, error_code = Errors.wrong_default_argument(arg_name,
                                                                                      command_name)
                            if self.handle_error(error_message, error_code, file_path=self.file_path):
                                self.is_valid = False
                                flag = False
                        if not arg.get('isArray'):
                            error_message, error_code = Errors.wrong_is_array_argument(arg_name,
                                                                                       command_name)
                            if self.handle_error(error_message, error_code, file_path=self.file_path):
                                self.is_valid = False
                                flag = False

                flag_found_required = command_mapping.get('required', True)
                if not flag_found_arg and flag_found_required:
                    error_message, error_code = Errors.no_default_arg(command_name)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        flag = False

        if not flag:
            print_error(Errors.suggest_fix(self.file_path))
        return flag

    def is_valid_default_argument(self):
        # type: () -> bool
        """Check if a  command has at most 1 default argument.

        Returns:
            bool. Whether a command holds at most 1 default argument.
        """
        is_valid = True
        commands = self.current_file.get('script', {}).get('commands', [])
        if commands is None:
            commands = []

        for command in commands:
            default_args = set()
            for arg in command.get('arguments', []):
                if arg.get('default'):
                    default_args.add(arg.get('name'))
            if len(default_args) > 1:  # if more than one default arg, command is faulty
                error_message, error_code = Errors.multiple_default_arg(command.get('name'), str(default_args))
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False  # do not break the main loop as there can be multiple invalid commands

        return is_valid

    @staticmethod
    def _get_invalid_dbot_outputs(context_outputs_paths, context_outputs_descriptions):
        missing_outputs = set()
        missing_descriptions = set()
        for dbot_score_output in DBOT_SCORES_DICT:
            if dbot_score_output not in context_outputs_paths:
                missing_outputs.add(dbot_score_output)
            else:  # DBot Score output path is in the outputs
                if DBOT_SCORES_DICT.get(dbot_score_output) not in context_outputs_descriptions:
                    missing_descriptions.add(dbot_score_output)
                    # self.is_valid = False - Do not fail build over wrong description

        return missing_outputs, missing_descriptions

    def is_outputs_for_reputations_commands_valid(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url)
            has the correct DBotScore outputs according to the context standard
            https://xsoar.pan.dev/docs/integrations/context-standards

        Returns:
            bool. Whether a reputation command holds valid outputs
        """
        context_standard = XSOAR_CONTEXT_STANDARD_URL
        commands = self.current_file.get('script', {}).get('commands', [])
        output_for_reputation_valid = True
        for command in commands:
            command_name = command.get('name')
            # look for reputations commands
            if command_name in BANG_COMMAND_NAMES:
                context_outputs_paths = set()
                context_outputs_descriptions = set()
                for output in command.get('outputs', []):
                    context_outputs_paths.add(output.get('contextPath'))
                    context_outputs_descriptions.add(output.get('description'))

                # validate DBotScore outputs and descriptions
                if command_name in REPUTATION_COMMAND_NAMES:
                    missing_outputs, missing_descriptions = self._get_invalid_dbot_outputs(
                        context_outputs_paths, context_outputs_descriptions)
                    if missing_outputs:
                        error_message, error_code = Errors.dbot_invalid_output(command_name, missing_outputs,
                                                                               context_standard)
                        if self.handle_error(error_message, error_code, file_path=self.file_path,
                                             warning=self.structure_validator.quite_bc):
                            self.is_valid = False
                            output_for_reputation_valid = False

                    if missing_descriptions:
                        error_message, error_code = Errors.dbot_invalid_description(command_name,
                                                                                    missing_descriptions,
                                                                                    context_standard)
                        self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)

                # validate the IOC output
                reputation_output = IOC_OUTPUTS_DICT.get(command_name)
                if reputation_output and not reputation_output.intersection(context_outputs_paths):
                    error_message, error_code = Errors.missing_reputation(command_name, reputation_output,
                                                                          context_standard)
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        self.is_valid = False
                        output_for_reputation_valid = False

        return output_for_reputation_valid

    def is_valid_subtype(self):
        # type: () -> bool
        """Validate that the subtype is python2 or python3."""
        type_ = self.current_file.get('script', {}).get('type')
        if type_ == 'python':
            subtype = self.current_file.get('script', {}).get('subtype')
            if subtype not in PYTHON_SUBTYPES:
                error_message, error_code = Errors.wrong_subtype()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    return False

        return True

    def is_changed_subtype(self):
        # type: () -> bool
        """Validate that the subtype was not changed."""
        type_ = self.current_file.get('script', {}).get('type')
        if type_ == 'python':
            subtype = self.current_file.get('script', {}).get('subtype')
            if self.old_file:
                old_subtype = self.old_file.get('script', {}).get('subtype', "")
                if old_subtype and old_subtype != subtype:
                    error_message, error_code = Errors.breaking_backwards_subtype()
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        self.is_valid = False
                        return True

        return False

    def is_valid_beta(self):
        # type: () -> bool
        """Validate that beta integration has correct beta attributes"""
        valid_status = True
        if not all([self._is_display_contains_beta(), self._has_beta_param()]):
            self.is_valid = False
            valid_status = False
        if not self.old_file:
            if not all([self._id_has_no_beta_substring(), self._name_has_no_beta_substring()]):
                self.is_valid = False
                valid_status = False
        return valid_status

    def _id_has_no_beta_substring(self):
        # type: () -> bool
        """Checks that 'id' field dose not include the substring 'beta'"""
        common_fields = self.current_file.get('commonfields', {})
        integration_id = common_fields.get('id', '')
        if 'beta' in integration_id.lower():
            error_message, error_code = Errors.beta_in_id()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def _name_has_no_beta_substring(self):
        # type: () -> bool
        """Checks that 'name' field dose not include the substring 'beta'"""
        name = self.current_file.get('name', '')
        if 'beta' in name.lower():
            error_message, error_code = Errors.beta_in_name()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def _has_beta_param(self):
        # type: () -> bool
        """Checks that integration has 'beta' field with value set to true"""
        beta = self.current_file.get('beta', False)
        if not beta:
            error_message, error_code = Errors.beta_field_not_found()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def _is_display_contains_beta(self):
        # type: () -> bool
        """Checks that 'display' field includes the substring 'beta'"""
        if not self.current_file.get('deprecated'):  # this validation is not needed for deprecated beta integrations
            display = self.current_file.get('display', '')
            if 'beta' not in display.lower():
                error_message, error_code = Errors.no_beta_in_display()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    def has_no_duplicate_args(self):
        # type: () -> bool
        """Check if a command has the same arg more than once

        Returns:
            bool. True if there are no duplicates, False if duplicates exist.
        """
        commands = self.current_file.get('script', {}).get('commands', [])
        does_not_have_duplicate_args = True
        for command in commands:
            arg_names = []  # type: list
            for arg in command.get('arguments', []):
                arg_name = arg.get('name')
                if arg_name in arg_names:
                    error_message, error_code = Errors.duplicate_arg_in_file(arg_name, command['name'])
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        does_not_have_duplicate_args = False

                else:
                    arg_names.append(arg_name)

        return does_not_have_duplicate_args

    def no_incident_in_core_packs(self):
        """check if commands' name or argument contains the word incident"""

        commands = self.current_file.get('script', {}).get('commands', [])
        commands_with_incident = []
        args_with_incident: Dict[str, list] = {}
        no_incidents = True
        for command in commands:
            command_name = command.get('name', '')
            if 'incident' in command_name:
                commands_with_incident.append(command_name)
            args = command.get('arguments', [])
            for arg in args:
                arg_name = arg.get("name")
                if 'incident' in arg_name:
                    args_with_incident.setdefault(command_name, []).append(arg_name)

        if commands_with_incident or args_with_incident:
            error_message, error_code = Errors.incident_in_command_name_or_args(commands_with_incident,
                                                                                args_with_incident)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_server_allowlist_fix()):
                self.is_valid = False
                no_incidents = False

        return no_incidents

    def has_no_duplicate_params(self):
        # type: () -> bool
        """Check if the integration has the same param more than once

        Returns:
            bool. True if there are no duplicates, False if duplicates exist.
        """
        does_not_have_duplicate_param = True
        configurations = self.current_file.get('configuration', [])
        param_list = set()
        for configuration_param in configurations:
            param_name = configuration_param['name']
            if param_name in param_list:
                error_message, error_code = Errors.duplicate_param(param_name)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    does_not_have_duplicate_param = False

            else:
                param_list.add(param_name)

        return does_not_have_duplicate_param

    @staticmethod
    def _get_command_to_args(integration_json):
        # type: (dict) -> dict
        """Get a dictionary command name to it's arguments.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's arguments.
        """
        command_to_args = {}  # type: dict
        commands = integration_json.get('script', {}).get('commands', [])
        for command in commands:
            command_to_args[command['name']] = {}
            for arg in command.get('arguments', []):
                command_to_args[command['name']][arg['name']] = arg.get('required', False)
        return command_to_args

    def is_changed_command_name_or_arg(self):
        # type: () -> bool
        """Check if a command name or argument as been changed.

        Returns:
            bool. Whether a command name or argument as been changed.
        """
        current_command_to_args = self._get_command_to_args(self.current_file)
        old_command_to_args = self._get_command_to_args(self.old_file)

        for command, args_dict in old_command_to_args.items():
            if command not in current_command_to_args.keys() or \
                    not self.is_subset_dictionary(current_command_to_args[command], args_dict):
                error_message, error_code = Errors.breaking_backwards_command_arg_changed(command)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     warning=self.structure_validator.quite_bc):
                    self.is_valid = False
                    return True

        return False

    @staticmethod
    def _is_sub_set(supposed_bigger_list, supposed_smaller_list):
        # type: (list, list) -> bool
        """Check if supposed_smaller_list is a subset of the supposed_bigger_list"""
        return all(item in supposed_bigger_list for item in supposed_smaller_list)

    def _get_command_to_context_paths(self, integration_json):
        # type: (dict) -> dict
        """Get a dictionary command name to it's context paths.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's context paths.
        """
        command_to_context_dict = {}
        commands = integration_json.get('script', {}).get('commands', [])
        for command in commands:
            context_list = []
            outputs = command.get('outputs', None)
            if not outputs:
                continue
            for output in outputs:
                command_name = command['name']
                try:
                    context_list.append(output['contextPath'])
                except KeyError:
                    error_message, error_code = Errors.invalid_context_output(command_name, output)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False

            command_to_context_dict[command['name']] = sorted(context_list)
        return command_to_context_dict

    def is_changed_context_path(self):
        # type: () -> bool
        """Check if a context path as been changed.

        Returns:
            bool. Whether a context path as been changed.
        """
        current_command_to_context_paths = self._get_command_to_context_paths(self.current_file)
        old_command_to_context_paths = self._get_command_to_context_paths(self.old_file)
        # if old integration command has no outputs, no change of context will occur.
        if not old_command_to_context_paths:
            return False
        # if new integration command has no outputs, and old one does, a change of context will occur.
        if not current_command_to_context_paths and old_command_to_context_paths \
                and not self.structure_validator.quite_bc:
            return True
        for old_command, old_context_paths in old_command_to_context_paths.items():
            if old_command in current_command_to_context_paths.keys():
                if not self._is_sub_set(current_command_to_context_paths[old_command], old_context_paths):
                    error_message, error_code = Errors.breaking_backwards_command(old_command)
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        self.is_valid = False
                        return True

        return False

    def is_removed_integration_parameters(self):
        # type: () -> bool
        """Check if integration parameters were removed."""
        is_removed_parameter = False
        current_configuration = self.current_file.get('configuration', [])
        old_configuration = self.old_file.get('configuration', [])
        current_param_names = {param.get('name') for param in current_configuration}
        old_param_names = {param.get('name') for param in old_configuration}
        if not old_param_names.issubset(current_param_names):
            removed_parameters = old_param_names - current_param_names
            error_message, error_code = Errors.removed_integration_parameters(repr(removed_parameters))
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                self.is_valid = False
                is_removed_parameter = True

        return is_removed_parameter

    @staticmethod
    def _get_field_to_required_dict(integration_json):
        """Get a dictionary field name to its required status.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. Field name to its required status.
        """
        field_to_required = {}
        configuration = integration_json.get('configuration', [])
        for field in configuration:
            field_to_required[field.get('name')] = field.get('required', False)
        return field_to_required

    def is_changed_removed_yml_fields(self):
        """checks if some specific Fields in the yml file were changed from true to false or removed"""
        fields = ['feed', 'isfetch', 'longRunning', 'longRunningPort', 'ismappable', 'isremotesyncin',
                  'isremotesyncout']
        currentscript = self.current_file.get('script', {})
        oldscript = self.old_file.get('script', {})

        removed, changed = {}, {}

        for field in fields:
            old = oldscript.get(field)
            current = currentscript.get(field)

            if old is not None and old is True:  # the field exists in old file and is true
                if current is None:  # the field was removed from current
                    removed[field] = old
                elif not current:  # changed from true to false
                    changed[field] = old

        if removed or changed:
            error_message, error_code = Errors.changed_integration_yml_fields(repr(removed), repr(changed))
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                self.is_valid = False
                return True
        return False

    def is_added_required_fields(self):
        # type: () -> bool
        """Check if required field were added."""
        current_field_to_required = self._get_field_to_required_dict(self.current_file)
        old_field_to_required = self._get_field_to_required_dict(self.old_file)
        is_added_required = False
        for field, required in current_field_to_required.items():
            if field in old_field_to_required.keys():
                # if required is True and old_field is False.
                if required and required != old_field_to_required[field]:
                    error_message, error_code = Errors.added_required_fields(field)
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        self.is_valid = False
                        is_added_required = True

            # if required is True but no old field.
            elif required:
                error_message, error_code = Errors.added_required_fields(field)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     warning=self.structure_validator.quite_bc):
                    self.is_valid = False
                    is_added_required = True

        return is_added_required

    def is_id_equals_name(self):
        """Check whether the integration's ID is equal to its name

        Returns:
            bool. Whether the integration's id equals to its name
        """
        return super(IntegrationValidator, self)._is_id_equals_name('integration')

    def is_not_valid_display_configuration(self):
        """Validate that the display settings are not empty for non-hidden fields and for type 17 params.

        Returns:
            bool. Whether the display is there for non-hidden fields.
        """
        configuration = self.current_file.get('configuration', [])
        for configuration_param in configuration:
            field_type = configuration_param['type']
            is_field_hidden = configuration_param.get('hidden', False)
            configuration_display = configuration_param.get('display')

            # This parameter type will not use the display value.
            if field_type == self.EXPIRATION_FIELD_TYPE:
                if configuration_display:
                    error_message, error_code = Errors.not_used_display_name(configuration_param['name'])
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        self.is_valid = False
                        return True

            elif not is_field_hidden and not configuration_display and not configuration_param.get('displaypassword') \
                    and configuration_param['name'] not in ('feedExpirationPolicy', 'feedExpirationInterval'):
                error_message, error_code = Errors.empty_display_configuration(configuration_param['name'])
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     warning=self.structure_validator.quite_bc):
                    self.is_valid = False
                    return True

        return False

    def is_docker_image_valid(self):
        # type: () -> bool
        # dockers should not be checked when running on all files
        if self.skip_docker_check:
            return True
        is_iron_bank = is_iron_bank_pack(self.file_path)
        docker_image_validator = DockerImageValidator(self.file_path, is_modified_file=True, is_integration=True,
                                                      ignored_errors=self.ignored_errors,
                                                      print_as_warnings=self.print_as_warnings,
                                                      suppress_print=self.suppress_print,
                                                      json_file_path=self.json_file_path,
                                                      is_iron_bank=is_iron_bank)

        # making sure we don't show error of validation if fetching is failed.
        _, error_code = Errors.docker_tag_not_fetched('', '')
        if f'{self.file_path} - [{error_code}]' in FOUND_FILES_AND_ERRORS:
            return False

        if docker_image_validator.is_docker_image_valid():
            return True

        self.is_valid = False
        return False

    def is_valid_feed(self):
        # type: () -> bool
        valid_from_version = valid_feed_params = True
        if self.current_file.get("script", {}).get("feed"):
            from_version = self.current_file.get("fromversion", "0.0.0")
            if not from_version or server_version_compare("5.5.0", from_version) == 1:
                error_message, error_code = Errors.feed_wrong_from_version(from_version)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path, '--from-version', '5.5.0')):
                    valid_from_version = False

            valid_feed_params = self.all_feed_params_exist()
        return valid_from_version and valid_feed_params

    def is_valid_pwsh(self) -> bool:
        if self.current_file.get("script", {}).get("type") == TYPE_PWSH:
            from_version = self.current_file.get("fromversion", "0.0.0")
            if not from_version or server_version_compare("5.5.0", from_version) > 0:
                error_message, error_code = Errors.pwsh_wrong_version(from_version)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path, '--from-version', '5.5.0')):
                    return False
        return True

    def is_valid_fetch(self) -> bool:
        """
        validate that all required fields in integration that have fetch incidents are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.current_file.get('script', {}).get('isfetch') is True:
            params = [dict.copy(_key) for _key in self.current_file.get('configuration', [])]
            for param in params:
                if 'defaultvalue' in param:
                    param.pop('defaultvalue')
            for param in FETCH_REQUIRED_PARAMS:
                if param not in params:
                    error_message, error_code = Errors.parameter_missing_from_yml(param.get('name'),
                                                                                  yaml.dump(param))
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         suggested_fix=Errors.suggest_fix(self.file_path)):
                        fetch_params_exist = False

        return fetch_params_exist

    def is_valid_max_fetch_and_first_fetch(self) -> bool:
        """
        validate that the max_fetch and first_fetch params exist in the yml and the max_fetch has default value
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.current_file.get('script', {}).get('isfetch') is True:
            params = self.current_file.get('configuration', [])
            first_fetch_param = None
            max_fetch_param = None
            for param in params:
                # the common names for the first_fetch param
                if param.get('name') == FIRST_FETCH:
                    first_fetch_param = param
                elif param.get('name') == MAX_FETCH:
                    max_fetch_param = param

            if not first_fetch_param:
                error_message, error_code = Errors.parameter_missing_from_yml_not_community_contributor(
                    'first_fetch', yaml.dump(FIRST_FETCH_PARAM))
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    fetch_params_exist = False

            if not max_fetch_param:
                error_message, error_code = Errors.parameter_missing_from_yml_not_community_contributor(
                    'max_fetch', yaml.dump(MAX_FETCH_PARAM))
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    fetch_params_exist = False

            elif not max_fetch_param.get("defaultvalue"):
                error_message, error_code = Errors.no_default_value_in_parameter('max_fetch')
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    fetch_params_exist = False

        return fetch_params_exist

    def all_feed_params_exist(self) -> bool:
        """
        validate that all required fields in feed integration are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        params_exist = True
        # Build params in efficient way of param_name: {param_field_name: param_field_value} to query quickly for param.
        params = {
            param.get('name'): {k: v for k, v in param.items()} for param in self.current_file.get('configuration', [])}

        for param_name, param_details in params.items():
            if 'defaultvalue' in param_details and param_name != 'feed':
                param_details.pop('defaultvalue')
            if 'hidden' in param_details:
                param_details.pop('hidden')

        for required_param in FEED_REQUIRED_PARAMS:
            is_valid = False
            param_details = params.get(required_param.get('name'))  # type: ignore
            equal_key_values: Dict = required_param.get('must_equal', dict())  # type: ignore
            contained_key_values: Dict = required_param.get('must_contain', dict())  # type: ignore
            if param_details:
                # Check length to see no unexpected key exists in the config. Add +1 for the 'name' key.
                is_valid = len(equal_key_values) + len(contained_key_values) + 1 == len(param_details) and all(
                    k in param_details and param_details[k] == v for k, v in equal_key_values.items()) and all(
                    k in param_details and v in param_details[k]
                    for k, v in contained_key_values.items())
            if not is_valid:
                param_structure = dict(equal_key_values, **contained_key_values, name=required_param.get('name'))
                error_message, error_code = Errors.parameter_missing_for_feed(required_param.get('name'),
                                                                              yaml.dump(param_structure))
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path)):
                    params_exist = False

        return params_exist

    def is_valid_display_name(self):
        # type: () -> bool
        version_number: Optional[str] = get_file_version_suffix_if_exists(self.current_file,
                                                                          check_in_display=True)
        if not version_number:
            return True
        else:
            display_name = self.current_file.get('display')
            correct_name = f' v{version_number}'
            if not display_name.endswith(correct_name):  # type: ignore
                error_message, error_code = Errors.invalid_version_integration_name(version_number)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

            return True

    def is_valid_hidden_params(self) -> bool:
        """
        Verify there are no non-allowed hidden integration parameters.
        Returns:
            bool. True if there aren't non-allowed hidden parameters. False otherwise.
        """
        ans = True
        conf = self.current_file.get('configuration', [])
        for int_parameter in conf:
            is_param_hidden = int_parameter.get('hidden')
            param_name = int_parameter.get('name')
            if is_param_hidden and param_name not in self.ALLOWED_HIDDEN_PARAMS:
                error_message, error_code = Errors.found_hidden_param(param_name)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    ans = False

        return ans

    def is_valid_image(self) -> bool:
        """Verifies integration image/logo is valid.

        Returns:
            bool. True if integration image/logo is valid, False otherwise.
        """
        image_validator = ImageValidator(self.file_path, ignored_errors=self.ignored_errors,
                                         print_as_warnings=self.print_as_warnings,
                                         json_file_path=self.json_file_path)
        if not image_validator.is_valid():
            return False
        return True

    def is_valid_description(self, beta_integration: bool = False) -> bool:
        """Verifies integration description is valid.

        Returns:
            bool: True if description is valid, False otherwise.
        """
        description_validator = DescriptionValidator(self.file_path, ignored_errors=self.ignored_errors,
                                                     print_as_warnings=self.print_as_warnings,
                                                     json_file_path=self.json_file_path)
        if beta_integration:
            if not description_validator.is_valid_beta_description():
                return False
        else:
            if not description_validator.is_valid_file():
                return False
        return True

    def is_there_a_runnable(self) -> bool:
        """Verifies there's at least one runnable command.
            at least one of:
            command in commands section
            isFetch
            feed
            long-running

        Returns:
            if there's at least one runnable in the yaml
        """
        script = self.current_file.get('script', {})

        if not any([
            script.get('commands'), script.get('isfetch', script.get('isFetch')), script.get("feed"),
            script.get('longRunning')]
        ):
            self.is_valid = False
            error, code = Errors.integration_not_runnable()
            self.handle_error(error, code, file_path=self.file_path)
            return False
        return True

    def is_valid_parameters_display_name(self) -> bool:
        """Verifies integration parameters display name is valid.

        Returns:
            bool: True if description is valid - capitalized and spaced using whitespace and not underscores,
            False otherwise.
        """
        configuration = self.current_file.get('configuration', {})
        parameters_display_name = [param.get('display') for param in configuration if param.get('display')]

        invalid_display_names = []
        for parameter in parameters_display_name:
            invalid_display_names.append(parameter) if parameter and not parameter[0].isupper() or '_' in parameter \
                else None

        if invalid_display_names:
            error_message, error_code = Errors.invalid_integration_parameters_display_name(invalid_display_names)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def is_valid_integration_file_path(self) -> bool:
        absolute_file_path = self.file_path
        integrations_folder = os.path.basename(os.path.dirname(absolute_file_path))
        integration_file = os.path.basename(absolute_file_path)

        # drop file extension
        integration_file, _ = os.path.splitext(integration_file)

        if integrations_folder == 'Integrations':
            if not integration_file.startswith('integration-'):

                error_message, error_code = \
                    Errors.is_valid_integration_file_path_in_integrations_folder(integration_file)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        elif integration_file != integrations_folder:
            valid_integration_file = integration_file.replace('-', '').replace('_', '')

            if valid_integration_file.lower() != integrations_folder.lower():
                error_message, error_code = Errors.is_valid_integration_file_path_in_folder(integration_file)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    def is_mapping_fields_command_exist(self) -> bool:
        """
        Check if get-mapping-fields command exists in the YML if  the ismappble field is set to true
        Returns:
            True if get-mapping-fields commands exist in the yml, else False.
        """
        script = self.current_file.get('script', {})
        if script.get('ismappable'):
            command_names = {command['name'] for command in script.get('commands', [])}
            if 'get-mapping-fields' not in command_names:
                error, code = Errors.missing_get_mapping_fields_command()
                if self.handle_error(error, code, file_path=self.file_path):
                    self.is_valid = False
                    return False
        return True

    def is_context_correct_in_readme(self) -> bool:
        """
        Checks if there has been a corresponding change to the integration's README
        when changing the context paths of an integration.
        This validation might run together with is_context_different_in_yml in Readme's validation.

        Returns:
            True if there has been a corresponding change to README file when context is changed in integration
        """
        valid = True

        dir_path = os.path.dirname(self.file_path)
        if not os.path.exists(os.path.join(dir_path, 'README.md')):
            return True

        # Only run validation if the validation has not run with is_context_different_in_yml on readme
        # so no duplicates errors will be created:
        error, missing_from_readme_error_code = Errors.readme_missing_output_context('', '')
        error, missing_from_yml_error_code = Errors.missing_output_context('', '')
        readme_path = os.path.join(dir_path, 'README.md')

        if f'{readme_path} - [{missing_from_readme_error_code}]' in FOUND_FILES_AND_IGNORED_ERRORS \
                or f'{readme_path} - [{missing_from_readme_error_code}]' in FOUND_FILES_AND_ERRORS \
                or f'{self.file_path} - [{missing_from_yml_error_code}]' in FOUND_FILES_AND_IGNORED_ERRORS \
                or f'{self.file_path} - [{missing_from_yml_error_code}]' in FOUND_FILES_AND_ERRORS:
            return False

        # get README file's content
        with open(readme_path, 'r') as readme:
            readme_content = readme.read()

        # commands = self.current_file.get("script", {}).get('commands', [])
        difference = compare_context_path_in_yml_and_readme(self.current_file, readme_content)
        for command_name in difference:
            if difference[command_name].get('only in yml'):
                error, code = Errors.readme_missing_output_context(
                    command_name,
                    ", ".join(difference[command_name].get('only in yml')))
                if self.handle_error(error, code, file_path=readme_path):
                    valid = False

            if difference[command_name].get('only in readme'):
                error, code = Errors.missing_output_context(command_name,
                                                            ", ".join(difference[command_name].get('only in readme')))
                if self.handle_error(error, code, file_path=self.file_path):
                    valid = False

        return valid

    def is_there_separators_in_names(self) -> bool:
        """
        Check if there are separators in the integration folder or files.

        Returns:
            true if the folder/files names are valid and there are no separators, and false if not.
        """
        is_unified_integration = self.current_file.get('script', {}).get('script', '') not in ['-', '']

        if is_unified_integration:
            return True

        answers = [
            self.check_separators_in_folder(),
            self.check_separators_in_files()
        ]

        return all(answers)

    def check_separators_in_folder(self) -> bool:
        """
        Check if there are separators in the integration folder.

        Returns:
            true if the name is valid and there are no separators, and false if not.
        """

        integration_folder_name = os.path.basename(os.path.dirname(self.file_path))
        valid_folder_name = self.remove_separators_from_name(integration_folder_name)

        if valid_folder_name != integration_folder_name:
            error_message, error_code = Errors.folder_name_has_separators('integration', integration_folder_name,
                                                                          valid_folder_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def check_separators_in_files(self):
        """
        Check if there are separators in the integration files names.

        Returns:
            true if the files names are valid and there is no separators, and false if not.
        """

        # Gets the all integration files that may have the integration name as base name
        files_to_check = get_files_in_dir(os.path.dirname(self.file_path), ['yml', 'py', 'md', 'png'], False)
        invalid_files = []
        valid_files = []

        for file_path in files_to_check:

            file_name = os.path.basename(file_path)
            if file_name.startswith('README'):
                continue

            if file_name.endswith('_image.png') or file_name.endswith('_description.md') or \
                    file_name.endswith('_test.py') or file_name.endswith('_unified.yml'):
                base_name = file_name.rsplit('_', 1)[0]

            else:
                base_name = file_name.rsplit('.', 1)[0]

            valid_base_name = self.remove_separators_from_name(base_name)

            if valid_base_name != base_name:
                invalid_files.append(file_name)
                valid_files.append(valid_base_name.join(file_name.rsplit(base_name, 1)))

        if invalid_files:

            error_message, error_code = Errors.file_name_has_separators('integration', invalid_files, valid_files)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def name_not_contain_the_type(self):
        """
        Check that the entity name or display name does not contain the entity type
        Returns: True if the name is valid
        """

        name = self.current_file.get('name', '')
        display_name = self.current_file.get('display', '')
        field_names = []
        if 'integration' in name.lower():
            field_names.append('name')
        if 'integration' in display_name.lower():
            field_names.append('display')

        if field_names:
            error_message, error_code = Errors.field_contain_forbidden_word(
                field_names=field_names, word='integration')

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_valid_endpoint_command(self):
        """
        Check if the endpoint command in yml is valid by standard.
        This command is separated than other reputation command as the inputs are different standard.

        Returns:
            true if the inputs and outputs are valid.
        """
        commands = self.current_file.get('script', {}).get('commands', [])

        if 'endpoint' not in [x.get('name') for x in commands]:
            return True

        # extracting the specific command from commands.
        endpoint_command = [arg for arg in commands if arg.get('name') == 'endpoint'][0]
        return self._is_valid_endpoint_inputs(endpoint_command, required_arguments=ENDPOINT_FLEXIBLE_REQUIRED_ARGS)

    def _is_valid_endpoint_inputs(self, command_data, required_arguments):
        """
        Check if the input for endpoint commands includes at least one required_arguments,
        and that only ip is the default argument.
        Returns:
            true if the inputs are valid.
        """
        endpoint_command_inputs = command_data.get('arguments', [])
        existing_arguments = {arg['name'] for arg in endpoint_command_inputs}

        # checking at least one of the required argument is found as argument
        if not set(required_arguments).intersection(existing_arguments):
            error_message, error_code = Errors.reputation_missing_argument(list(required_arguments),
                                                                           command_data.get('name'),
                                                                           all=False)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        # checking no other arguments are default argument:
        default_args_found = [(arg.get('name'), arg.get('default', False)) for arg in endpoint_command_inputs]
        command_default_arg_map = BANG_COMMAND_ARGS_MAPPING_DICT[ENDPOINT_COMMAND_NAME]
        default_arg_name = command_default_arg_map['default']
        other_default_args_found = list(filter(
            lambda x: x[1] is True and x[0] not in default_arg_name, default_args_found))
        if other_default_args_found:
            error_message, error_code = Errors.wrong_default_argument(default_arg_name, ENDPOINT_COMMAND_NAME)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

    def default_params_have_default_additional_info(self):
        """Check if the all integration params that can have a default description have a it set.
        Raises warnings if the additional info is defined (not empty) but is different from the default.

        Returns:
            bool: True if all relevant params have an additional info value
                  False if at least one param that can have a default additionalInfo has an empty one.
        """
        params_missing_defaults = []
        params_with_non_default_description = []

        additional_info = {param['name']: param.get('additionalinfo', '')
                           for param in self.current_file.get('configuration', [])}

        for param, info in additional_info.items():
            if param in default_additional_info and info != default_additional_info[param]:
                if not info:
                    params_missing_defaults.append(param)
                else:
                    params_with_non_default_description.append(param)
        if params_with_non_default_description:
            non_default_error_message, non_default_error_code = \
                Errors.non_default_additional_info(params_with_non_default_description)
            self.handle_error(non_default_error_message, non_default_error_code, file_path=self.file_path, warning=True)

        if params_missing_defaults:
            missing_error_message, missing_error_code = Errors.missing_default_additional_info(params_missing_defaults)
            self.handle_error(missing_error_message, missing_error_code, self.current_file,
                              suggested_fix=Errors.suggest_fix(self.file_path))
            return False
        return True

    def is_api_token_in_credential_type(self):
        conf_params = self.current_file.get('configuration', [])
        for param in conf_params:
            if param.get('type') == 4:
                error_message, error_code = Errors.api_token_is_not_in_credential_type(param.get('name'))
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True
