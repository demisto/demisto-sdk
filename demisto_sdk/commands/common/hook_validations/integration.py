import yaml
from demisto_sdk.commands.common.constants import (BANG_COMMAND_NAMES,
                                                   DBOT_SCORES_DICT,
                                                   FEED_REQUIRED_PARAMS,
                                                   FETCH_REQUIRED_PARAMS,
                                                   INTEGRATION_CATEGORIES,
                                                   IOC_OUTPUTS_DICT,
                                                   PYTHON_SUBTYPES, TYPE_PWSH)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.description import \
    DescriptionValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.utils import is_v2_file
from demisto_sdk.commands.common.tools import (print_error,
                                               server_version_compare)


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
        if self.handle_error(error_message, error_code, file_path=self.file_path):
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
            self.is_added_required_fields(),
            self.is_changed_command_name_or_arg(),
            self.is_there_duplicate_args(),
            self.is_there_duplicate_params(),
            self.is_changed_subtype(),
            self.is_not_valid_display_configuration(),
            # will move to is_valid_integration after https://github.com/demisto/etc/issues/17949
            not self.is_outputs_for_reputations_commands_valid()
        ]
        return not any(answers)

    def is_valid_file(self, validate_rn: bool = True, skip_test_conf: bool = False) -> bool:
        """Check whether the Integration is valid or not

            Args:
                validate_rn (bool): Whether to validate release notes (changelog) or not.
                skip_test_conf (bool): If true then will skip test playbook configuration validation

            Returns:
                bool: True if integration is valid, False otherwise.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_subtype(),
            self.is_valid_default_arguments(),
            self.is_proxy_configured_correctly(),
            self.is_insecure_configured_correctly(),
            self.is_checkbox_param_configured_correctly(),
            self.is_valid_category(),
            self.is_id_equals_name(),
            self.is_docker_image_valid(),
            self.is_valid_feed(),
            self.is_valid_fetch(),
            self.is_valid_display_name(),
            self.is_valid_hidden_params(),
            self.is_valid_pwsh(),
            self.is_valid_image(),
            self.is_valid_description(beta_integration=False),
        ]

        if not skip_test_conf:
            answers.append(self.are_tests_configured())

        return all(answers)

    def are_tests_configured(self) -> bool:
        """
        Checks if the integration has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        tests = self.current_file.get('tests', [])
        return self.are_tests_registered_in_conf_json_file_or_yml_file(tests)

    def is_valid_beta_integration(self, validate_rn: bool = True) -> bool:
        """Check whether the beta Integration is valid or not, update the _is_valid field to determine that
            Args:
                validate_rn (bool): Whether to validate release notes (changelog) or not.

            Returns:
                bool: True if integration is valid, False otherwise.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_default_arguments(),
            self.is_valid_beta(),
            self.is_valid_image(),
            self.is_valid_description(beta_integration=True),
        ]
        return all(answers)

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

                if configuration_param.get('defaultvalue', '') not in ('false', ''):
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
            print_error('{} Received the following error for {} validation:\n{}'
                        .format(self.file_path, param_name, '\n'.join(err_msgs)))
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

    def is_valid_default_arguments(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url)
            has a default non required argument with the same name

        Returns:
            bool. Whether a reputation command hold a valid argument
        """
        commands = self.current_file.get('script', {}).get('commands', [])
        flag = True
        for command in commands:
            command_name = command.get('name')
            if command_name in BANG_COMMAND_NAMES:
                flag_found_arg = False
                for arg in command.get('arguments', []):
                    arg_name = arg.get('name')
                    if arg_name == command_name:
                        flag_found_arg = True
                        if arg.get('default') is False:
                            error_message, error_code = Errors.wrong_default_argument(arg_name,
                                                                                      command_name)
                            if self.handle_error(error_message, error_code, file_path=self.file_path):
                                self.is_valid = False
                                flag = False

                if not flag_found_arg:
                    error_message, error_code = Errors.no_default_arg(command_name)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        flag = False

        if not flag:
            print_error(Errors.suggest_fix(self.file_path))
        return flag

    def is_outputs_for_reputations_commands_valid(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url)
            has the correct DBotScore outputs according to the context standard
            https://xsoar.pan.dev/docs/integrations/context-standards

        Returns:
            bool. Whether a reputation command holds valid outputs
        """
        context_standard = "https://xsoar.pan.dev/docs/integrations/context-standards"
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
                missing_outputs = set()
                missing_descriptions = set()
                for dbot_score_output in DBOT_SCORES_DICT:
                    if dbot_score_output not in context_outputs_paths:
                        missing_outputs.add(dbot_score_output)
                    else:  # DBot Score output path is in the outputs
                        if DBOT_SCORES_DICT.get(dbot_score_output) not in context_outputs_descriptions:
                            missing_descriptions.add(dbot_score_output)
                            # self.is_valid = False - Do not fail build over wrong description

                if missing_outputs:
                    error_message, error_code = Errors.dbot_invalid_output(command_name, missing_outputs,
                                                                           context_standard)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        output_for_reputation_valid = False

                if missing_descriptions:
                    error_message, error_code = Errors.dbot_invalid_description(command_name, missing_descriptions,
                                                                                context_standard)
                    self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)

                # validate the IOC output
                reputation_output = IOC_OUTPUTS_DICT.get(command_name)
                if reputation_output and not reputation_output.intersection(context_outputs_paths):
                    error_message, error_code = Errors.missing_reputation(command_name, reputation_output,
                                                                          context_standard)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
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
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        return True

        return False

    def is_valid_beta(self):
        # type: () -> bool
        """Validate that that beta integration has correct beta attributes"""

        if not all([self._is_display_contains_beta(), self._has_beta_param()]):
            self.is_valid = False
            return False
        if self.old_file:
            if not all([self._id_has_no_beta_substring(), self._name_has_no_beta_substring()]):
                self.is_valid = False
                return False
        return True

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
        display = self.current_file.get('display', '')
        if 'beta' not in display.lower():
            error_message, error_code = Errors.no_beta_in_display()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def is_there_duplicate_args(self):
        # type: () -> bool
        """Check if a command has the same arg more than once

        Returns:
            bool. True if there are duplicates, False otherwise.
        """
        commands = self.current_file.get('script', {}).get('commands', [])
        is_there_duplicates = False
        for command in commands:
            arg_list = []  # type: list
            for arg in command.get('arguments', []):
                if arg in arg_list:
                    error_message, error_code = Errors.duplicate_arg_in_file(arg['name'], command['name'])
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        is_there_duplicates = True

                else:
                    arg_list.append(arg)

        return is_there_duplicates

    def is_there_duplicate_params(self):
        # type: () -> bool
        """Check if the integration has the same param more than once

        Returns:
            bool. True if there are duplicates, False otherwise.
        """
        has_duplicate_params = False
        configurations = self.current_file.get('configuration', [])
        param_list = []  # type: list
        for configuration_param in configurations:
            param_name = configuration_param['name']
            if param_name in param_list:
                error_message, error_code = Errors.duplicate_param(param_name)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    has_duplicate_params = True

            else:
                param_list.append(param_name)

        return has_duplicate_params

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
                if self.handle_error(error_message, error_code, file_path=self.file_path):
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
        if not current_command_to_context_paths and old_command_to_context_paths:
            return True
        for old_command, old_context_paths in old_command_to_context_paths.items():
            if old_command in current_command_to_context_paths.keys():
                if not self._is_sub_set(current_command_to_context_paths[old_command], old_context_paths):
                    error_message, error_code = Errors.breaking_backwards_command(old_command)
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        return True

        return False

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
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        is_added_required = True

            # if required is True but no old field.
            elif required:
                error_message, error_code = Errors.added_required_fields(field)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
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
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self.is_valid = False
                        return True

            elif not is_field_hidden and not configuration_display \
                    and configuration_param['name'] not in ('feedExpirationPolicy', 'feedExpirationInterval'):
                error_message, error_code = Errors.empty_display_configuration(configuration_param['name'])
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    return True

        return False

    def is_docker_image_valid(self):
        # type: () -> bool
        # dockers should not be checked when running on all files
        if self.skip_docker_check:
            return True

        docker_image_validator = DockerImageValidator(self.file_path, is_modified_file=True, is_integration=True,
                                                      ignored_errors=self.ignored_errors,
                                                      print_as_warnings=self.print_as_warnings)
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
            params = [_key for _key in self.current_file.get('configuration', [])]
            for param in params:
                if 'defaultvalue' in param:
                    param.pop('defaultvalue')
            for param in FETCH_REQUIRED_PARAMS:
                if param not in params:
                    error_message, error_code = Errors.parameter_missing_from_yml(param.get('name'),
                                                                                  yaml.dump(param))
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
        params = [_key for _key in self.current_file.get('configuration', [])]
        for counter, param in enumerate(params):
            if 'defaultvalue' in param and param['name'] != 'feed':
                params[counter].pop('defaultvalue')
            if 'hidden' in param:
                params[counter].pop('hidden')
        for param in FEED_REQUIRED_PARAMS:
            if param not in params:
                error_message, error_code = Errors.parameter_missing_for_feed(param.get('name'), yaml.dump(param))
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    params_exist = False

        return params_exist

    def is_valid_display_name(self):
        # type: () -> bool
        if not is_v2_file(self.current_file):
            return True
        else:
            display_name = self.current_file.get('display')
            correct_name = " v2"
            if not display_name.endswith(correct_name):
                error_message, error_code = Errors.invalid_v2_integration_name()
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
                                         print_as_warnings=self.print_as_warnings)
        if not image_validator.is_valid():
            return False
        return True

    def is_valid_description(self, beta_integration: bool = False) -> bool:
        """Verifies integration description is valid.

        Returns:
            bool: True if description is valid, False otherwise.
        """
        description_validator = DescriptionValidator(self.file_path, ignored_errors=self.ignored_errors,
                                                     print_as_warnings=self.print_as_warnings)
        if beta_integration:
            if not description_validator.is_valid_beta_description():
                return False
        else:
            if not description_validator.is_valid():
                return False
        return True
