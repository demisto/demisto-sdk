import json
import os
import tempfile
from typing import Optional, Union

import click
import demisto_client
from demisto_sdk.commands.common.constants import (BANG_COMMAND_NAMES,
                                                   BETA_INTEGRATION_DISCLAIMER,
                                                   CONF_PATH, DBOT_SCORES_DICT,
                                                   DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   FEED_REQUIRED_PARAMS,
                                                   FETCH_REQUIRED_PARAMS,
                                                   FIRST_FETCH,
                                                   FIRST_FETCH_PARAM,
                                                   INTEGRATION,
                                                   INTEGRATION_CATEGORIES,
                                                   IOC_OUTPUTS_DICT, MAX_FETCH,
                                                   MAX_FETCH_PARAM,
                                                   OLDEST_SUPPORTED_VERSION,
                                                   PYTHON_SUBTYPES, TYPE_PWSH,
                                                   FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.content.objects.pack_objects.image.image import \
    Image
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.tools import (get_demisto_version,
                                               get_old_file,
                                               is_test_config_match,
                                               is_v2_file)
from packaging.version import Version, parse
from ruamel import yaml
from wcmatch.pathlib import Path

EXPIRATION_FIELD_TYPE = 17
ALLOWED_HIDDEN_PARAMS = {'longRunning', 'feedIncremental', 'feedReputation'}


def _load_conf_file():
    with open(CONF_PATH) as data_file:
        return json.load(data_file)


class Integration(YAMLContentUnifiedObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, FileType.INTEGRATION, INTEGRATION)
        self.base = base if base else BaseValidator()

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_image.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_description.md"]
        return next(self._path.parent.glob(patterns=patterns), None)

    def upload(self, client: demisto_client = None):
        """
        Upload the integration to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if self.is_unify():
            return client.integration_upload(file=self.path)  # type: ignore
        else:
            with tempfile.TemporaryDirectory() as dir:
                unified_files = self._unify(dir)
                for file in unified_files:
                    if (str(file)[-7:] == '_45.yml') == (get_demisto_version(client) < parse('4.6.0')):
                        # The above condition checks that the file ends in `_45.yml' and the version is 4.5 or less
                        # or that the file doesn't end in `_45.yml` and the version is higher than 4.5
                        return client.integration_upload(file=file)  # type: ignore

    def validate(self):
        old_file = get_old_file(self.path, self.base.old_file_path, self.base.prev_ver, suppress_print=True)

        if self.check_if_integration_is_deprecated():
            click.echo(f"Validating deprecated file: {self.path}")
            valid_deprecated = self.is_valid_as_deprecated()
            if self.base.check_bc:
                return all([valid_deprecated, self.is_backward_compatible(old_file)])
            else:
                return valid_deprecated

        if self.base.file_type == FileType.BETA_INTEGRATION:
            return self.is_valid_beta_integration(old_file)

        if self.base.check_bc:
            return self.is_valid_file() and self.is_backward_compatible(old_file)
        else:
            return self.is_valid_file()

    def is_backward_compatible(self, old_file):
        """Check whether the Integration is backward compatible or not, update the _is_valid field to determine that"""
        if not old_file:
            return True

        answers = [
            self.is_changed_context_path(old_file=old_file),
            self.is_removed_integration_parameters(old_file=old_file),
            self.is_added_required_fields(old_file=old_file),
            self.is_changed_command_name_or_arg(old_file=old_file),
            self.is_changed_subtype(old_file=old_file)
        ]
        return not any(answers)

    def is_valid_file(self) -> bool:
        """Check whether the Integration is valid or not according to the LEVEL SUPPORT OPTIONS
        that depends on the contributor type

            Returns:
                bool: True if integration is valid, False otherwise.
        """

        answers = [
            self.is_valid_version(),
            self.is_valid_fromversion(),
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
            self.is_there_a_runnable(),
            self.is_valid_display_name(),
            self.is_valid_hidden_params(),
            self.is_valid_pwsh(),
            self.is_valid_image(),
            self.is_duplicate_description(),
            self.is_valid_max_fetch_and_first_fetch(),
            self.is_valid_deprecated_integration_display_name(),
            self.is_valid_deprecated_integration_description(),
            self.is_mapping_fields_command_exist(),
            self.is_there_duplicate_args(),
            self.is_there_duplicate_params(),
            self.is_outputs_for_reputations_commands_valid(),
            self.is_not_valid_display_configuration()
        ]

        if not self.base.skip_test_conf:
            answers.append(self.are_tests_configured())
        return all(answers)

    def check_if_integration_is_deprecated(self):
        is_deprecated = self.get('deprecated', False)

        toversion_is_old = self.to_version < Version(OLDEST_SUPPORTED_VERSION)

        return is_deprecated or toversion_is_old

    def is_valid_as_deprecated(self):
        """Check if the integration is valid as a deprecated integration."""

        answers = [
            self.is_valid_deprecated_integration_display_name(),
            self.is_valid_deprecated_integration_description(),
        ]
        return all(answers)

    def is_valid_version(self):
        # type: () -> bool
        if self.get("commonfields", {}).get('version') == DEFAULT_VERSION:
            return True

        error_message, error_code = Errors.wrong_version()
        if self.base.handle_error(error_message, error_code, file_path=self.path):
            return False

        return True

    def is_valid_subtype(self):
        # type: () -> bool
        """Validate that the subtype is python2 or python3."""
        type_ = self.get('script', {}).get('type')
        if type_ == 'python':
            subtype = self.get('script', {}).get('subtype')
            if subtype not in PYTHON_SUBTYPES:
                error_message, error_code = Errors.wrong_subtype()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        return True

    def is_valid_default_arguments(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url)
            has a default non required argument with the same name

        Returns:
            bool. Whether a reputation command hold a valid argument
        """
        commands = self.get('script', {}).get('commands', [])
        if commands is None:
            commands = []
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
                            if self.base.handle_error(error_message, error_code, file_path=self.path):
                                flag = False

                if not flag_found_arg:
                    error_message, error_code = Errors.no_default_arg(command_name)
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        flag = False

        if not flag:
            click.secho(Errors.suggest_fix(self.path), fg='bright_red')
        return flag

    def is_proxy_configured_correctly(self):
        # type: () -> bool
        """Check that if an integration has a proxy parameter that it is configured properly."""
        return self.is_valid_param('proxy', 'Use system proxy settings')

    def is_insecure_configured_correctly(self):
        # type: () -> bool
        """Check that if an integration has an insecure parameter that it is configured properly."""
        insecure_field_name = ''
        configuration = self.get('configuration', [])
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
        is_valid = True
        configuration = self.get('configuration', [])
        for configuration_param in configuration:
            param_name = configuration_param['name']
            if configuration_param['type'] == 8 and param_name not in ('insecure', 'unsecure', 'proxy', 'isFetch'):
                if not self.is_valid_checkbox_param(configuration_param, param_name):
                    is_valid = False

        return is_valid

    def is_valid_param(self, param_name, param_display):
        # type: (str, str) -> bool
        """Check if the given parameter has the right configuration."""
        err_msgs = []
        configuration = self.get('configuration', [])
        for configuration_param in configuration:
            configuration_param_name = configuration_param['name']
            if configuration_param_name == param_name:
                if configuration_param['display'] != param_display:
                    error_message, error_code = Errors.wrong_display_name(param_name, param_display)
                    formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
                                                               should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('defaultvalue', '') not in ('false', ''):
                    error_message, error_code = Errors.wrong_default_parameter_not_empty(param_name, "''")
                    formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
                                                               should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('required', False):
                    error_message, error_code = Errors.wrong_required_value(param_name)
                    formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
                                                               should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get('type') != 8:
                    error_message, error_code = Errors.wrong_required_type(param_name)
                    formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
                                                               should_print=False)
                    if formatted_message:
                        err_msgs.append(formatted_message)

        if err_msgs:
            err_msgs_str = "\n".join(err_msgs)
            click.secho(f'{str(self.path)} Received the following error for '
                        f'{param_name} validation:\n{err_msgs_str}', fg='bright_red')
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
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_category(self):
        # type: () -> bool
        """Check that the integration category is in the schema."""
        category = self.get('category', None)
        if category not in INTEGRATION_CATEGORIES:
            error_message, error_code = Errors.wrong_category(category)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def is_id_equals_name(self):
        """Validate that the id of the file equals to the name.
         Args:

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self.get('commonfields', {}).get('id')
        name = self.get('name', '')
        if file_id != name:
            error_message, error_code = Errors.id_should_equal_name(name, file_id)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False

        return True

    def is_docker_image_valid(self):
        # dockers should not be checked when running on all files
        if self.base.skip_docker_check:
            return True

        docker_image_validator = DockerImageValidator(str(self.path), is_modified_file=True, is_integration=True,
                                                      ignored_errors=self.base.ignored_errors,
                                                      print_as_warnings=self.base.print_as_warnings)
        if docker_image_validator.is_docker_image_valid():
            return True

        return False

    def is_valid_feed(self):
        # type: () -> bool
        valid_from_version = valid_feed_params = True
        if self.get("script", {}).get("feed"):
            from_version = self.get("fromversion")
            if not from_version or self.from_version < Version('5.5.0'):
                error_message, error_code = Errors.feed_wrong_from_version(from_version)
                if self.base.handle_error(error_message, error_code, file_path=self.path,
                                          suggested_fix=Errors.suggest_fix(self.path, '--from-version', '5.5.0')):
                    valid_from_version = False

            valid_feed_params = self.all_feed_params_exist()
        return valid_from_version and valid_feed_params

    def all_feed_params_exist(self) -> bool:
        """
        validate that all required fields in feed integration are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        params_exist = True
        params = [_key for _key in self.get('configuration', [])]
        for counter, param in enumerate(params):
            if 'defaultvalue' in param and param['name'] != 'feed':
                params[counter].pop('defaultvalue')
            if 'hidden' in param:
                params[counter].pop('hidden')
        for param in FEED_REQUIRED_PARAMS:
            if param not in params:
                error_message, error_code = Errors.parameter_missing_for_feed(param.get('name'), yaml.dump(param))
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    params_exist = False

        return params_exist

    def is_valid_fetch(self) -> bool:
        """
        validate that all required fields in integration that have fetch incidents are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.get('script', {}).get('isfetch') is True:
            params = [dict.copy(_key) for _key in self.get('configuration', [])]
            for param in params:
                if 'defaultvalue' in param:
                    param.pop('defaultvalue')
            for param in FETCH_REQUIRED_PARAMS:
                if param not in params:
                    error_message, error_code = Errors.parameter_missing_from_yml(param.get('name'),
                                                                                  yaml.dump(param))
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        fetch_params_exist = False

        return fetch_params_exist

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
        script = self.get('script', {})

        if not any([
            script.get('commands'), script.get('isfetch', script.get('isFetch')), script.get("feed"),
            script.get('longRunning')]
        ):
            error, code = Errors.integration_not_runnable()
            if self.base.handle_error(error, code, file_path=self.path):
                return False
        return True

    def is_valid_display_name(self):
        # type: () -> bool
        if not is_v2_file(self, check_in_display=True):
            return True
        else:
            display_name = self.get('display')
            correct_name = " v2"
            if not display_name.endswith(correct_name):  # type: ignore
                error_message, error_code = Errors.invalid_v2_integration_name()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

            return True

    def is_valid_hidden_params(self) -> bool:
        """
        Verify there are no non-allowed hidden integration parameters.
        Returns:
            bool. True if there aren't non-allowed hidden parameters. False otherwise.
        """
        ans = True
        conf = self.get('configuration', [])
        for int_parameter in conf:
            is_param_hidden = int_parameter.get('hidden')
            param_name = int_parameter.get('name')
            if is_param_hidden and param_name not in ALLOWED_HIDDEN_PARAMS:
                error_message, error_code = Errors.found_hidden_param(param_name)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    ans = False

        return ans

    def is_valid_pwsh(self) -> bool:
        if self.get("script", {}).get("type") == TYPE_PWSH:
            from_version = self.get("fromversion", "0.0.0")
            if not from_version or self.from_version < Version('5.5.0'):
                error_message, error_code = Errors.pwsh_wrong_version(from_version)
                if self.base.handle_error(error_message, error_code, file_path=self.path,
                                          suggested_fix=Errors.suggest_fix(self.path, '--from-version', '5.5.0')):
                    return False
        return True

    def is_valid_image(self) -> bool:
        """Verifies integration image/logo is valid.

        Returns:
            bool. True if integration image/logo is valid, False otherwise.
        """
        return Image(self.path, self.base).validate()

    def is_valid_max_fetch_and_first_fetch(self) -> bool:
        """
        validate that the max_fetch and first_fetch params exist in the yml and the max_fetch has default value
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.get('script', {}).get('isfetch') is True:
            params = self.get('configuration', [])
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
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    fetch_params_exist = False

            if not max_fetch_param:
                error_message, error_code = Errors.parameter_missing_from_yml_not_community_contributor(
                    'max_fetch', yaml.dump(MAX_FETCH_PARAM))
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    fetch_params_exist = False

            elif not max_fetch_param.get("defaultvalue"):
                error_message, error_code = Errors.no_default_value_in_parameter('max_fetch')
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    fetch_params_exist = False

        return fetch_params_exist

    def is_valid_deprecated_integration_display_name(self) -> bool:
        is_valid = True
        is_deprecated = self.get('deprecated', False)
        display_name = self.get('display', '')
        if is_deprecated:
            if not display_name.endswith('(Deprecated)'):
                error_message, error_code = Errors.invalid_deprecated_integration_display_name()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_valid = False
        return is_valid

    def is_valid_deprecated_integration_description(self) -> bool:
        is_valid = True
        is_deprecated = self.get('deprecated', False)
        description = self.get('description', '')
        if is_deprecated:
            if not description.startswith('Deprecated.'):
                error_message, error_code = Errors.invalid_deprecated_integration_description()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_valid = False
        return is_valid

    def is_mapping_fields_command_exist(self) -> bool:
        """
        Check if get-mapping-fields command exists in the YML if  the ismappble field is set to true
        Returns:
            True if get-mapping-fields commands exist in the yml, else False.
        """
        script = self.get('script', {})
        if script.get('ismappable'):
            command_names = {command['name'] for command in script.get('commands', [])}
            if 'get-mapping-fields' not in command_names:
                error, code = Errors.missing_get_mapping_fields_command()
                if self.base.handle_error(error, code, file_path=self.path):
                    return False
        return True

    def are_tests_configured(self) -> bool:
        """
        Checks if the integration has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        tests = self.get('tests', [])
        return self.are_tests_registered_in_conf_json_file_or_yml_file(tests)

    def are_tests_registered_in_conf_json_file_or_yml_file(self, test_playbooks: list) -> bool:
        """
        If the file is a test playbook:
            Validates it is registered in conf.json file
        If the file is an integration:
            Validating it is registered in conf.json file or that the yml file has 'No tests' under 'tests' key
        Args:
            test_playbooks: The yml file's list of test playbooks

        Returns:
            True if all test playbooks are configured in conf.json
        """
        no_tests_explicitly = any(test for test in test_playbooks if 'no test' in test.lower())
        if no_tests_explicitly:
            return True
        conf_json_tests = _load_conf_file()['tests']

        content_item_id = self.get('commonfields', {}).get('id')

        # Integration case
        is_configured_test = any(
            test_config for test_config in conf_json_tests if is_test_config_match(test_config,
                                                                                   integration_id=content_item_id))
        if not is_configured_test:
            missing_test_playbook_configurations = json.dumps(
                {'integrations': content_item_id, 'playbookID': '<TestPlaybook ID>'},
                indent=4)
            no_tests_key = yaml.dump({'tests': ['No tests']})
            error_message, error_code = Errors.integration_not_registered(self.path,
                                                                          missing_test_playbook_configurations,
                                                                          no_tests_key)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
            return False

        return True

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromversion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def _get_command_to_context_paths(self, integration_json=None):
        # type: (dict) -> Union[dict, bool]
        """Get a dictionary command name to it's context paths.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's context paths.
        """
        if integration_json is None:
            integration_json = {}
        command_to_context_dict = {}
        if integration_json:
            commands = integration_json.get('script', {}).get('commands', [])
        else:
            commands = self.get('script', {}).get('commands', [])
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
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        return False
            command_to_context_dict[command['name']] = sorted(context_list)
        return command_to_context_dict

    @staticmethod
    def _is_sub_set(supposed_bigger_list, supposed_smaller_list):
        # type: (list, list) -> bool
        """Check if supposed_smaller_list is a subset of the supposed_bigger_list"""
        return all(item in supposed_bigger_list for item in supposed_smaller_list)

    def is_changed_context_path(self, old_file):
        # type: (dict) -> bool
        """Check if a context path as been changed.

        Returns:
            bool. Whether a context path as been changed.
        """
        current_command_to_context_paths = self._get_command_to_context_paths()
        old_command_to_context_paths = self._get_command_to_context_paths(old_file)

        # there was an invalid context output somewhere
        if isinstance(old_command_to_context_paths, bool) or isinstance(current_command_to_context_paths, bool):
            return True

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
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        return True

        return False

    def is_removed_integration_parameters(self, old_file):
        # type: (dict) -> bool
        """Check if integration parameters were removed."""
        is_removed_parameter = False
        current_configuration = self.get('configuration', [])
        old_configuration = old_file.get('configuration', [])
        current_param_names = {param.get('name') for param in current_configuration}
        old_param_names = {param.get('name') for param in old_configuration}
        if not old_param_names.issubset(current_param_names):
            removed_parameters = old_param_names - current_param_names
            error_message, error_code = Errors.removed_integration_parameters(repr(removed_parameters))
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_removed_parameter = True

        return is_removed_parameter

    def _get_field_to_required_dict(self, integration_json=None):
        """Get a dictionary field name to its required status.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. Field name to its required status.
        """
        if integration_json is None:
            integration_json = {}
        field_to_required = {}
        if integration_json:
            configuration = integration_json.get('configuration', [])
        else:
            configuration = self.get('configuration', [])
        for field in configuration:
            field_to_required[field.get('name')] = field.get('required', False)
        return field_to_required

    def is_added_required_fields(self, old_file):
        # type: (dict) -> bool
        """Check if required field were added."""
        current_field_to_required = self._get_field_to_required_dict()
        old_field_to_required = self._get_field_to_required_dict(old_file)
        is_added_required = False
        for field, required in current_field_to_required.items():
            if field in old_field_to_required.keys():
                # if required is True and old_field is False.
                if required and required != old_field_to_required[field]:
                    error_message, error_code = Errors.added_required_fields(field)
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        is_added_required = True

            # if required is True but no old field.
            elif required:
                error_message, error_code = Errors.added_required_fields(field)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_added_required = True

        return is_added_required

    def _get_command_to_args(self, integration_json=None):
        # type: (dict) -> dict
        """Get a dictionary command name to it's arguments.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's arguments.
        """
        command_to_args = {}  # type: dict
        if integration_json:
            commands = integration_json.get('script', {}).get('commands', [])
        else:
            commands = self.get('script', {}).get('commands', [])
        for command in commands:
            command_to_args[command['name']] = {}
            for arg in command.get('arguments', []):
                command_to_args[command['name']][arg['name']] = arg.get('required', False)
        return command_to_args

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

    def is_changed_command_name_or_arg(self, old_file):
        # type: (dict) -> bool
        """Check if a command name or argument as been changed.

        Returns:
            bool. Whether a command name or argument as been changed.
        """
        current_command_to_args = self._get_command_to_args()
        old_command_to_args = self._get_command_to_args(old_file)

        for command, args_dict in old_command_to_args.items():
            if command not in current_command_to_args.keys() or \
                    not self.is_subset_dictionary(current_command_to_args[command], args_dict):
                error_message, error_code = Errors.breaking_backwards_command_arg_changed(command)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return True

        return False

    def is_there_duplicate_args(self):
        # type: () -> bool
        """Check if a command has the same arg more than once

        Returns:
            bool. False if there are duplicates, True otherwise.
        """
        commands = self.get('script', {}).get('commands', [])
        no_duplicates = True
        for command in commands:
            arg_list = []  # type: list
            for arg in command.get('arguments', []):
                if arg in arg_list:
                    error_message, error_code = Errors.duplicate_arg_in_file(arg['name'], command['name'])
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        no_duplicates = False

                else:
                    arg_list.append(arg)

        return no_duplicates

    def is_there_duplicate_params(self):
        # type: () -> bool
        """Check if the integration has the same param more than once

        Returns:
            bool. False if there are duplicates, True otherwise.
        """
        no_duplicate_params = True
        configurations = self.get('configuration', [])
        param_list = []  # type: list
        for configuration_param in configurations:
            param_name = configuration_param['name']
            if param_name in param_list:
                error_message, error_code = Errors.duplicate_param(param_name)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    no_duplicate_params = False

            else:
                param_list.append(param_name)

        return no_duplicate_params

    def is_changed_subtype(self, old_file):
        # type: (dict) -> bool
        """Validate that the subtype was not changed."""
        type_ = self.get('script', {}).get('type')
        if type_ == 'python':
            subtype = self.get('script', {}).get('subtype')
            if old_file:
                old_subtype = old_file.get('script', {}).get('subtype', "")
                if old_subtype and old_subtype != subtype:
                    error_message, error_code = Errors.breaking_backwards_subtype()
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        return True

        return False

    def is_not_valid_display_configuration(self):
        """Validate that the display settings are not empty for non-hidden fields and for type 17 params.

        Returns:
            bool. Whether the display is there for non-hidden fields.
        """
        configuration = self.get('configuration', [])
        for configuration_param in configuration:
            field_type = configuration_param['type']
            is_field_hidden = configuration_param.get('hidden', False)
            configuration_display = configuration_param.get('display')

            # This parameter type will not use the display value.
            if field_type == EXPIRATION_FIELD_TYPE:
                if configuration_display:
                    error_message, error_code = Errors.not_used_display_name(configuration_param['name'])
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        return False

            elif not is_field_hidden and not configuration_display \
                    and configuration_param['name'] not in ('feedExpirationPolicy', 'feedExpirationInterval'):
                error_message, error_code = Errors.empty_display_configuration(configuration_param['name'])
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        return True

    def is_outputs_for_reputations_commands_valid(self):
        # type: () -> bool
        """Check if a reputation command (domain/email/file/ip/url)
            has the correct DBotScore outputs according to the context standard
            https://xsoar.pan.dev/docs/integrations/context-standards

        Returns:
            bool. Whether a reputation command holds valid outputs
        """
        context_standard = "https://xsoar.pan.dev/docs/integrations/context-standards"
        commands = self.get('script', {}).get('commands', [])
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
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        output_for_reputation_valid = False

                if missing_descriptions:
                    error_message, error_code = Errors.dbot_invalid_description(command_name, missing_descriptions,
                                                                                context_standard)
                    self.base.handle_error(error_message, error_code, file_path=self.path, warning=True)

                # validate the IOC output
                reputation_output = IOC_OUTPUTS_DICT.get(command_name)
                if reputation_output and not reputation_output.intersection(context_outputs_paths):
                    error_message, error_code = Errors.missing_reputation(command_name, reputation_output,
                                                                          context_standard)
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        output_for_reputation_valid = False

        return output_for_reputation_valid

    def is_valid_beta_integration(self, old_file) -> bool:
        """Check whether the beta Integration is valid or not, update the _is_valid field to determine that

            Returns:
                bool: True if integration is valid, False otherwise.
        """
        answers = [
            self.is_valid_version(),
            self.is_valid_fromversion(),
            self.is_valid_default_arguments(),
            self.is_valid_beta(old_file),
            self.is_valid_image(),
            self.is_valid_beta_description(),
        ]
        return all(answers)

    def is_valid_beta(self, old_file):
        # type: (dict) -> bool
        """Validate that beta integration has correct beta attributes"""
        valid_status = True
        if not all([self._is_display_contains_beta(), self._has_beta_param()]):
            valid_status = False
        if not old_file:
            if not all([self._id_has_no_beta_substring(), self._name_has_no_beta_substring()]):
                valid_status = False
        return valid_status

    def _id_has_no_beta_substring(self):
        # type: () -> bool
        """Checks that 'id' field dose not include the substring 'beta'"""
        common_fields = self.get('commonfields', {})
        integration_id = common_fields.get('id', '')
        if 'beta' in integration_id.lower():
            error_message, error_code = Errors.beta_in_id()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def _name_has_no_beta_substring(self):
        # type: () -> bool
        """Checks that 'name' field dose not include the substring 'beta'"""
        name = self.get('name', '')
        if 'beta' in name.lower():
            error_message, error_code = Errors.beta_in_name()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def _has_beta_param(self):
        # type: () -> bool
        """Checks that integration has 'beta' field with value set to true"""
        beta = self.get('beta', False)
        if not beta:
            error_message, error_code = Errors.beta_field_not_found()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def _is_display_contains_beta(self):
        # type: () -> bool
        """Checks that 'display' field includes the substring 'beta'"""
        display = self.get('display', '')
        if 'beta' not in display.lower():
            error_message, error_code = Errors.no_beta_in_display()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def is_duplicate_description(self):
        """Check if the integration has a non-duplicate description ."""
        is_description_in_yml = False
        is_description_in_package = False

        if os.path.exists(str(self.description_path)):
            is_description_in_package = True

        is_unified_integration = self.get('script', {}).get('script', '') not in {'-', ''}
        if not (self.get('deprecated') or is_unified_integration) and not is_description_in_package:
            error_message, error_code = Errors.no_description_file_warning()
            self.base.handle_error(error_message, error_code, file_path=self.path, warning=True)

        if self.get('detaileddescription'):
            is_description_in_yml = True

        if is_description_in_package and is_description_in_yml:
            error_message, error_code = Errors.description_in_package_and_yml()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def is_valid_beta_description(self):
        """Check if beta disclaimer exists in detailed description"""
        description_in_yml = self.get('detaileddescription', '')
        is_unified_integration = self.get('script', {}).get('script', '') not in {'-', ''}

        if not is_unified_integration:
            if not os.path.exists(str(self.description_path)):
                error_message, error_code = Errors.description_missing_in_beta_integration()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

            with open(str(self.description_path)) as description_file:
                description = description_file.read()
            if BETA_INTEGRATION_DISCLAIMER not in description:
                error_message, error_code = Errors.no_beta_disclaimer_in_description()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False
            else:
                return True

        elif BETA_INTEGRATION_DISCLAIMER not in description_in_yml:
            error_message, error_code = Errors.no_beta_disclaimer_in_yml()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True
