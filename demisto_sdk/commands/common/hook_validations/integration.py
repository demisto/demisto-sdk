import os
import re
from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    ALERT_FETCH_REQUIRED_PARAMS,
    ALLOWED_HIDDEN_PARAMS,
    BANG_COMMAND_ARGS_MAPPING_DICT,
    BANG_COMMAND_NAMES,
    DBOT_SCORES_DICT,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
    ENDPOINT_COMMAND_NAME,
    ENDPOINT_FLEXIBLE_REQUIRED_ARGS,
    FEED_REQUIRED_PARAMS,
    FIRST_FETCH,
    FIRST_FETCH_PARAM,
    INCIDENT_FETCH_REQUIRED_PARAMS,
    IOC_OUTPUTS_DICT,
    MANDATORY_REPUTATION_CONTEXT_NAMES,
    MAX_FETCH,
    MAX_FETCH_PARAM,
    PACKS_DIR,
    PACKS_PACK_META_FILE_NAME,
    PARTNER_SUPPORT,
    PYTHON_SUBTYPES,
    RELIABILITY_PARAMETER_NAMES,
    REPUTATION_COMMAND_NAMES,
    SUPPORT_LEVEL_HEADER,
    TYPE_PWSH,
    XSOAR_CONTEXT_STANDARD_URL,
    XSOAR_SUPPORT,
    MarketplaceVersions,
    ParameterType,
)
from demisto_sdk.commands.common.default_additional_info_loader import (
    load_default_additional_info_dict,
)
from demisto_sdk.commands.common.errors import (
    FOUND_FILES_AND_ERRORS,
    FOUND_FILES_AND_IGNORED_ERRORS,
    Errors,
)
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.hook_validations.description import (
    DescriptionValidator,
)
from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    _get_file_id,
    compare_context_path_in_yml_and_readme,
    extract_deprecated_command_names_from_yml,
    extract_none_deprecated_command_names_from_yml,
    get_core_pack_list,
    get_file_version_suffix_if_exists,
    get_files_in_dir,
    get_item_marketplaces,
    get_pack_name,
    is_iron_bank_pack,
    is_str_bool,
    server_version_compare,
    string_to_bool,
    strip_description,
)
from demisto_sdk.commands.validate.tools import (
    get_default_output_description,
)

default_additional_info = load_default_additional_info_dict()


class IntegrationValidator(ContentEntityValidator):
    """IntegrationValidator is designed to validate the correctness of the file structure we enter to content repo. And
    also try to catch possible Backward compatibility breaks due to the preformed changes.
    """

    def __init__(
        self,
        structure_validator,
        ignored_errors=None,
        skip_docker_check=False,
        json_file_path=None,
        validate_all=False,
        deprecation_validator=None,
        using_git=False,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            skip_docker_check=skip_docker_check,
        )
        self.running_validations_using_git = using_git
        self.validate_all = validate_all
        self.deprecation_validator = deprecation_validator

    @error_codes("BA100")
    def is_valid_version(self) -> bool:
        if (
            self.current_file.get("commonfields", {}).get("version")
            == self.DEFAULT_VERSION
        ):
            return True

        error_message, error_code = Errors.wrong_version()
        if self.handle_error(
            error_message,
            error_code,
            file_path=self.file_path,
            suggested_fix=Errors.suggest_fix(self.file_path),
        ):
            self.is_valid = False
            return False

        return True

    def is_backward_compatible(self) -> bool:
        """Check whether the Integration is backward compatible or not, update the _is_valid field to determine that"""
        if not self.old_file:
            return True

        answers = [
            super().is_backward_compatible(),
            self.no_change_to_context_path(),
            self.no_removed_integration_parameters(),
            self.no_added_required_fields(),
            self.no_changed_command_name_or_arg(),
            self.is_valid_display_configuration(),
            self.no_changed_removed_yml_fields(),
        ]
        return all(answers)

    def core_integration_validations(self, validate_rn: bool = True):
        """Perform the core integration validations (common to both beta and regular integrations)
        Args:
            validate_rn (bool): Whether to validate release notes (changelog) or not.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.validate_readme_exists(self.validate_all),
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
            self.is_valid_default_value_for_checkbox(),
            self.is_valid_display_name_for_siem(),
            self.is_valid_xsiam_marketplace(),
            self.is_valid_pwsh(),
            self.is_valid_image(),
            self.is_valid_max_fetch_and_first_fetch(),
            self.is_valid_as_deprecated(),
            self.is_valid_parameters_display_name(),
            self.is_valid_parameter_url_default_value(),
            self.is_mapping_fields_command_exist(),
            self.is_valid_integration_file_path(),
            self.is_valid_py_file_names(),
            self.has_no_duplicate_params(),
            self.has_no_duplicate_args(),
            self.is_there_separators_in_names(),
            self.name_not_contain_the_type(),
            self.is_valid_endpoint_command(),
            self.is_api_token_in_credential_type(),
            self.are_common_outputs_with_description(),
            self.is_native_image_does_not_exist_in_yml(),
            self.validate_unit_test_exists(),
            self.is_line_ends_with_dot(),
            self.is_partner_collector_has_xsoar_support_level_header(),
        ]

        return all(answers)

    def is_valid_file(
        self,
        validate_rn: bool = True,
        skip_test_conf: bool = False,
        check_is_unskipped: bool = True,
        conf_json_data: dict = {},
        is_modified=False,
    ) -> bool:
        """Check whether the Integration is valid or not according to the LEVEL SUPPORT OPTIONS
        that depends on the contributor type

            Args:
                validate_rn (bool): Whether to validate release notes (changelog) or not.
                skip_test_conf (bool): If true then will skip test playbook configuration validation
                check_is_unskipped (bool): Whether to check if the integration is unskipped.
                conf_json_data (dict): The conf.json file data.
                is_modified (bool): Wether the given files are modified or not.

            Returns:
                bool: True if integration is valid, False otherwise.
        """

        answers = [
            self.core_integration_validations(validate_rn),
            self.is_valid_hidden_params(),
            self.is_valid_description(beta_integration=False),
            self.is_context_correct_in_readme(),
            self.verify_yml_commands_match_readme(is_modified),
            self.verify_reputation_commands_has_reliability(),
            self.is_integration_deprecated_and_used(),
            self.is_outputs_for_reputations_commands_valid(),
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

    @error_codes("IN140")
    def is_unskipped_integration(self, conf_json_data):
        """Validated the integration testing is not skipped."""
        skipped_integrations = conf_json_data.get("skipped_integrations", {})
        integration_id = _get_file_id("integration", self.current_file)
        if skipped_integrations and integration_id in skipped_integrations:
            if "no instance" in skipped_integrations[
                integration_id
            ].lower() and not self.has_unittest(self.file_path):
                skip_comment = skipped_integrations[integration_id]
                error_message, error_code = Errors.integration_is_skipped(
                    integration_id, skip_comment
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = False
        return self.is_valid

    @error_codes("IN127,IN160")
    def _is_valid_deprecated_integration_display_name(self) -> bool:
        is_deprecated = self.current_file.get("deprecated", False)
        is_display_name_deprecated = self.current_file.get("display", "").endswith(
            "(Deprecated)"
        )

        if is_deprecated and (not is_display_name_deprecated):
            (
                error_message,
                error_code,
            ) = Errors.invalid_deprecated_integration_display_name()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        if (not is_deprecated) and is_display_name_deprecated:
            (
                error_message,
                error_code,
            ) = Errors.invalid_integration_deprecation__only_display_name_suffix(
                self.file_path
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @error_codes("IN128,IN158")
    def _is_valid_deprecated_integration_description(self) -> bool:
        is_deprecated = self.current_file.get("deprecated", False)
        description = self.current_file.get("description", "")

        description_indicates_deprecation = any(
            (
                re.search(DEPRECATED_DESC_REGEX, description),
                re.search(DEPRECATED_NO_REPLACE_DESC_REGEX, description),
            )
        )

        if is_deprecated and (not description_indicates_deprecation):
            (
                error_message,
                error_code,
            ) = Errors.invalid_deprecated_integration_description()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        if (not is_deprecated) and description_indicates_deprecation:
            (
                error_message,
                error_code,
            ) = Errors.invalid_deprecation__only_description_deprecated(self.file_path)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IN152")
    def is_valid_default_value_for_checkbox(self) -> bool:
        config = self.current_file.get("configuration", {})
        for param in config:
            if param.get("type") == 8:
                if param.get("defaultvalue") not in [None, "true", "false"]:
                    (
                        error_message,
                        error_code,
                    ) = Errors.invalid_defaultvalue_for_checkbox_field(
                        param.get("name")
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        return False
        return True

    def are_tests_configured(self) -> bool:
        """
        Checks if the integration has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        tests = self.current_file.get("tests", [])
        return self.are_tests_registered_in_conf_json_file_or_yml_file(tests)

    @error_codes("IN100,IN101,IN102,IN103")
    def is_valid_param(self, param_name: str, param_display: str) -> bool:
        """Check if the given parameter has the right configuration."""
        err_msgs = []
        configuration = self.current_file.get("configuration", [])
        for configuration_param in configuration:
            configuration_param_name = configuration_param["name"]
            if configuration_param_name == param_name:
                if configuration_param["display"] != param_display:
                    error_message, error_code = Errors.wrong_display_name(
                        param_name, param_display
                    )
                    formatted_message = self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                    )
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get("defaultvalue", "") not in (
                    False,
                    "false",
                    "",
                ):
                    (
                        error_message,
                        error_code,
                    ) = Errors.wrong_default_parameter_not_empty(param_name, "''")
                    formatted_message = self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                    )
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get("required", False):
                    error_message, error_code = Errors.wrong_required_value(param_name)
                    formatted_message = self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                    )
                    if formatted_message:
                        err_msgs.append(formatted_message)

                if configuration_param.get("type") != 8:
                    error_message, error_code = Errors.wrong_required_type(param_name)
                    formatted_message = self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                    )
                    if formatted_message:
                        err_msgs.append(formatted_message)

        if err_msgs:
            logger.error(
                "{} Received the following error for {} validation:\n{}\n {}\n".format(
                    self.file_path,
                    param_name,
                    "\n".join(err_msgs),
                    Errors.suggest_fix(file_path=self.file_path),
                )
            )
            self.is_valid = False
            return False
        return True

    def is_proxy_configured_correctly(self) -> bool:
        """Check that if an integration has a proxy parameter that it is configured properly."""
        return self.is_valid_param("proxy", "Use system proxy settings")

    def is_insecure_configured_correctly(self) -> bool:
        """Check that if an integration has an insecure parameter that it is configured properly."""
        insecure_field_name = ""
        configuration = self.current_file.get("configuration", [])
        for configuration_param in configuration:
            if configuration_param["name"] in ("insecure", "unsecure"):
                insecure_field_name = configuration_param["name"]
        if insecure_field_name:
            return self.is_valid_param(
                insecure_field_name, "Trust any certificate (not secure)"
            )
        return True

    def is_checkbox_param_configured_correctly(self) -> bool:
        """Check that if an integration has a checkbox parameter it is configured properly.
        Returns:
            bool. True if the checkbox parameter is configured correctly, False otherwise.
        """
        configuration = self.current_file.get("configuration", [])
        for configuration_param in configuration:
            param_name = configuration_param["name"]
            if configuration_param["type"] == 8 and param_name not in (
                "insecure",
                "unsecure",
                "proxy",
                "isFetch",
            ):
                if not self.is_valid_checkbox_param(configuration_param, param_name):
                    self.is_valid = False
        if not self.is_valid:
            return False
        return True

    @error_codes("IN102")
    def is_valid_checkbox_param(
        self, configuration_param: dict, param_name: str
    ) -> bool:
        """Check if the given checkbox parameter required field is False.
        Returns:
            bool. True if valid, False otherwise.
        """
        if configuration_param.get("required", False):
            error_message, error_code = Errors.wrong_required_value(param_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IN104")
    def is_valid_category(self) -> bool:
        """Check that the integration category is in the schema."""
        if tools.is_external_repository():
            return True
        category = self.current_file.get("category", None)
        approved_list = tools.get_current_categories()
        if category not in approved_list:
            error_message, error_code = Errors.wrong_category(category, approved_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    @error_codes("IN105,IN144,IN106")
    def is_valid_default_array_argument_in_reputation_command(self) -> bool:
        """Check if a reputation command (domain/email/file/ip/url/cve)
            has a default non required argument and make sure the default value can accept array of inputs.

        Returns:
            bool. Whether a reputation command hold a valid argument which support array.
        """
        commands = self.current_file.get("script", {}).get("commands", [])
        if commands is None:
            commands = []
        flag = True
        for command in commands:
            command_name = command.get("name", "")
            if command_name in BANG_COMMAND_NAMES:
                command_mapping = BANG_COMMAND_ARGS_MAPPING_DICT[command_name]
                flag_found_arg = False
                for arg in command.get("arguments", []):
                    arg_name = arg.get("name")
                    if arg_name in command_mapping["default"]:
                        flag_found_arg = True
                        if arg.get("default") is False:
                            error_message, error_code = Errors.wrong_default_argument(
                                arg_name, command_name
                            )
                            if self.handle_error(
                                error_message, error_code, file_path=self.file_path
                            ):
                                self.is_valid = False
                                flag = False
                        if not arg.get("isArray"):
                            error_message, error_code = Errors.wrong_is_array_argument(
                                arg_name, command_name
                            )
                            if self.handle_error(
                                error_message, error_code, file_path=self.file_path
                            ):
                                self.is_valid = False
                                flag = False

                flag_found_required = command_mapping.get("required", True)
                if not flag_found_arg and flag_found_required:
                    error_message, error_code = Errors.no_default_arg(command_name)
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        flag = False

        if not flag:
            logger.error(Errors.suggest_fix(self.file_path))
        return flag

    @error_codes("IN134")
    def is_valid_default_argument(self) -> bool:
        """Check if a  command has at most 1 default argument.

        Returns:
            bool. Whether a command holds at most 1 default argument.
        """
        is_valid = True
        commands = self.current_file.get("script", {}).get("commands", [])
        if commands is None:
            commands = []

        for command in commands:
            default_args = set()
            if command.get("arguments", []) is None:
                error_message, error_code = Errors.empty_command_arguments(
                    command.get("name")
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(self.file_path),
                ):
                    is_valid = False  # do not break the main loop as there can be multiple invalid commands
                    continue

            for arg in command.get("arguments", []):
                if arg.get("default"):
                    default_args.add(arg.get("name"))
            if len(default_args) > 1:  # if more than one default arg, command is faulty
                error_message, error_code = Errors.multiple_default_arg(
                    command.get("name"), str(default_args)
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
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
                if (
                    DBOT_SCORES_DICT.get(dbot_score_output)
                    not in context_outputs_descriptions
                ):
                    missing_descriptions.add(dbot_score_output)
                    # self.is_valid = False - Do not fail build over wrong description

        return missing_outputs, missing_descriptions

    def validate_reputation_name_spelling(
        self, command_name: str, context_output_path: str
    ) -> bool:
        """
        Validates that the context output for reputation outputs is spelled correctly.
        Args:
            command_name (str): The name of the command being validated.
            context_output_path (str): The path to the context output of a command.
        Returns:
            bool: True if the reputation name is spelled correctly, False otherwise."""
        result = True
        for reputation_name in MANDATORY_REPUTATION_CONTEXT_NAMES:
            # In context output we expect a dot after reputation name as this is the structure
            # of a valid context output: URL.DATA, Domain.Admin etc.
            if context_output_path.lower().startswith(f"{reputation_name.lower()}."):
                if reputation_name not in context_output_path:
                    (
                        error_message,
                        error_code,
                    ) = Errors.command_reputation_output_capitalization_incorrect(
                        command_name, context_output_path, reputation_name
                    )
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        result = False
        return result

    @error_codes("DB100,DB101,IN107,IN159")
    def is_outputs_for_reputations_commands_valid(self) -> bool:
        """Check if a reputation command (domain/email/file/ip/url)
            1. Has the correct DBotScore outputs according to the context standard
               https://xsoar.pan.dev/docs/integrations/context-standards
            2. Is spelled correctly.

        Returns:
            bool. Whether a reputation command holds valid outputs
        """
        context_standard = XSOAR_CONTEXT_STANDARD_URL
        commands = self.current_file.get("script", {}).get("commands", [])
        output_for_reputation_valid = True
        for command in commands:
            command_name = command.get("name")
            # look for reputations commands
            if command_name in BANG_COMMAND_NAMES:
                context_outputs_paths = set()
                context_outputs_descriptions = set()
                for output in command.get("outputs", []):
                    context_path = output.get("contextPath")
                    context_outputs_paths.add(context_path)
                    context_outputs_descriptions.add(output.get("description"))
                    output_for_reputation_valid = (
                        self.validate_reputation_name_spelling(
                            command_name, context_path
                        )
                    )

                # validate DBotScore outputs and descriptions
                if command_name in REPUTATION_COMMAND_NAMES:
                    (
                        missing_outputs,
                        missing_descriptions,
                    ) = self._get_invalid_dbot_outputs(
                        context_outputs_paths, context_outputs_descriptions
                    )
                    if missing_outputs:
                        error_message, error_code = Errors.dbot_invalid_output(
                            command_name, missing_outputs, context_standard
                        )
                        if self.handle_error(
                            error_message,
                            error_code,
                            file_path=self.file_path,
                            warning=self.structure_validator.quiet_bc,
                        ):
                            self.is_valid = False
                            output_for_reputation_valid = False

                    if missing_descriptions:
                        error_message, error_code = Errors.dbot_invalid_description(
                            command_name, missing_descriptions, context_standard
                        )
                        if self.handle_error(
                            error_message,
                            error_code,
                            file_path=self.file_path,
                            warning=True,
                        ):
                            self.is_valid = False
                            output_for_reputation_valid = False

                # validate the IOC output
                reputation_output = IOC_OUTPUTS_DICT.get(command_name)
                if reputation_output and not reputation_output.intersection(
                    context_outputs_paths
                ):
                    error_message, error_code = Errors.missing_reputation(
                        command_name, reputation_output, context_standard
                    )
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        self.is_valid = False
                        output_for_reputation_valid = False

        return output_for_reputation_valid

    @error_codes("IN108")
    def is_valid_subtype(self) -> bool:
        """Validate that the subtype is python2 or python3."""
        type_ = self.current_file.get("script", {}).get("type")
        if type_ == "python":
            subtype = self.current_file.get("script", {}).get("subtype")
            if subtype not in PYTHON_SUBTYPES:
                error_message, error_code = Errors.wrong_subtype()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = False
                    return False

        return True

    @error_codes("BC100")
    def no_changed_subtype(self) -> bool:
        """Validate that the subtype was not changed.
        Returns True if valid, and False otherwise."""
        type_ = self.current_file.get("script", {}).get("type")
        if type_ == "python":
            subtype = self.current_file.get("script", {}).get("subtype")
            if self.old_file:
                old_subtype = self.old_file.get("script", {}).get("subtype", "")
                if old_subtype and old_subtype != subtype:
                    error_message, error_code = Errors.breaking_backwards_subtype()
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        self.is_valid = False
                        return False

        return True

    def is_valid_beta(self) -> bool:
        """Validate that beta integration has correct beta attributes"""
        valid_status = True
        if not all([self._is_display_contains_beta(), self._has_beta_param()]):
            self.is_valid = False
            valid_status = False
        if not self.old_file:
            if not all(
                [self._id_has_no_beta_substring(), self._name_has_no_beta_substring()]
            ):
                self.is_valid = False
                valid_status = False
        return valid_status

    @error_codes("IN109")
    def _id_has_no_beta_substring(self) -> bool:
        """Checks that 'id' field dose not include the substring 'beta'"""
        common_fields = self.current_file.get("commonfields", {})
        integration_id = common_fields.get("id", "")
        if "beta" in integration_id.lower():
            error_message, error_code = Errors.beta_in_id()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @error_codes("IN110")
    def _name_has_no_beta_substring(self) -> bool:
        """Checks that 'name' field dose not include the substring 'beta'"""
        name = self.current_file.get("name", "")
        if "beta" in name.lower():
            error_message, error_code = Errors.beta_in_name()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @error_codes("IN111")
    def _has_beta_param(self) -> bool:
        """Checks that integration has 'beta' field with value set to true"""
        beta = self.current_file.get("beta", False)
        if not beta:
            error_message, error_code = Errors.beta_field_not_found()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @error_codes("IN112")
    def _is_display_contains_beta(self) -> bool:
        """Checks that 'display' field includes the substring 'beta'"""
        if not self.current_file.get(
            "deprecated"
        ):  # this validation is not needed for deprecated beta integrations
            display = self.current_file.get("display", "")
            if "beta" not in display.lower():
                error_message, error_code = Errors.no_beta_in_display()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    @error_codes("IN113")
    def has_no_duplicate_args(self) -> bool:
        """Check if a command has the same arg more than once

        Returns:
            bool. True if there are no duplicates, False if duplicates exist.
        """
        commands = self.current_file.get("script", {}).get("commands", [])
        does_not_have_duplicate_args = True
        for command in commands:
            # If this happens, an error message will be shown from is_valid_default_argument(), but still need to check
            # for it here to avoid crash
            if command.get("arguments", []) is None:
                continue
            arg_names: list = []
            for arg in command.get("arguments", []):
                arg_name = arg.get("name")
                if arg_name in arg_names:
                    error_message, error_code = Errors.duplicate_arg_in_file(
                        arg_name, command["name"]
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        self.is_valid = False
                        does_not_have_duplicate_args = False

                else:
                    arg_names.append(arg_name)

        return does_not_have_duplicate_args

    @error_codes("IN139")
    def no_incident_in_core_packs(self):
        """check if commands' name or argument contains the word incident"""

        commands = self.current_file.get("script", {}).get("commands", [])
        commands_with_incident = []
        args_with_incident: Dict[str, list] = {}
        no_incidents = True
        for command in commands:
            command_name = command.get("name", "")
            if "incident" in command_name:
                commands_with_incident.append(command_name)
            args = command.get("arguments", [])
            for arg in args:
                arg_name = arg.get("name")
                if "incident" in arg_name:
                    args_with_incident.setdefault(command_name, []).append(arg_name)

        if commands_with_incident or args_with_incident:
            error_message, error_code = Errors.incident_in_command_name_or_args(
                commands_with_incident, args_with_incident
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_server_allowlist_fix(),
            ):
                self.is_valid = False
                no_incidents = False

        return no_incidents

    @error_codes("IN114")
    def has_no_duplicate_params(self) -> bool:
        """Check if the integration has the same param more than once

        Returns:
            bool. True if there are no duplicates, False if duplicates exist.
        """
        does_not_have_duplicate_param = True
        configurations = self.current_file.get("configuration", [])
        param_list = set()
        for configuration_param in configurations:
            param_name = configuration_param["name"]
            if param_name in param_list:
                error_message, error_code = Errors.duplicate_param(param_name)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self.is_valid = False
                    does_not_have_duplicate_param = False

            else:
                param_list.add(param_name)

        return does_not_have_duplicate_param

    @staticmethod
    def _get_command_to_args(integration_json: dict) -> dict:
        """Get a dictionary command name to it's arguments.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's arguments.
        """
        command_to_args: dict = {}
        commands = integration_json.get("script", {}).get("commands", [])
        for command in commands:
            command_to_args[command["name"]] = {}
            for arg in command.get("arguments", []):
                command_to_args[command["name"]][arg["name"]] = arg.get(
                    "required", False
                )
        return command_to_args

    @error_codes("BC104")
    def no_changed_command_name_or_arg(self) -> bool:
        """Check if a command name or argument as been changed.

        Returns:
            bool. True if valid, and False otherwise.
        """
        changed_commands = []
        current_command_to_args = self._get_command_to_args(self.current_file)
        old_command_to_args = self._get_command_to_args(self.old_file)

        for command, args_dict in old_command_to_args.items():
            if (
                command not in current_command_to_args.keys()
                or not self.is_subset_dictionary(
                    current_command_to_args[command], args_dict
                )
            ):
                changed_commands.append(command)
        if changed_commands:
            error_message, error_code = Errors.breaking_backwards_command_arg_changed(
                changed_commands
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                self.is_valid = False
                return False
        return True

    @staticmethod
    def _is_sub_set(supposed_bigger_list: list, supposed_smaller_list: list) -> bool:
        """Check if supposed_smaller_list is a subset of the supposed_bigger_list"""
        return all(item in supposed_bigger_list for item in supposed_smaller_list)

    @error_codes("IN115")
    def _get_command_to_context_paths(self, integration_json: dict) -> dict:
        """Get a dictionary command name to it's context paths.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. command name to a list of it's context paths.
        """
        command_to_context_dict = {}
        commands = integration_json.get("script", {}).get("commands", [])
        for command in commands:
            context_list = []
            outputs = command.get("outputs", None)
            if not outputs:
                continue
            for output in outputs:
                command_name = command["name"]
                try:
                    context_list.append(output["contextPath"])
                except KeyError:
                    error_message, error_code = Errors.invalid_context_output(
                        command_name, output
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        self.is_valid = False

            command_to_context_dict[command["name"]] = sorted(context_list)
        return command_to_context_dict

    @error_codes("BC102")
    def no_change_to_context_path(self) -> bool:
        """Check if a context path as been changed.

        Returns:
            bool. True if valid, and False otherwise.
        """
        current_command_to_context_paths = self._get_command_to_context_paths(
            self.current_file
        )
        old_command_to_context_paths = self._get_command_to_context_paths(self.old_file)
        # if old integration command has no outputs, no change of context will occur.
        if not old_command_to_context_paths:
            return True
        no_change = True
        for old_command, old_context_paths in old_command_to_context_paths.items():
            if old_command in current_command_to_context_paths.keys():
                if not self._is_sub_set(
                    current_command_to_context_paths[old_command], old_context_paths
                ):
                    error_message, error_code = Errors.breaking_backwards_command(
                        old_command
                    )
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        self.is_valid = False
                        no_change = False
            else:
                error_message, error_code = Errors.breaking_backwards_command(
                    old_command
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    self.is_valid = False
                    no_change = False

        return no_change

    @error_codes("IN129")
    def no_removed_integration_parameters(self) -> bool:
        """Check if integration parameters were removed.
        Returns True if valid, and False otherwise.
        """
        no_removed_parameter = True
        current_configuration = self.current_file.get("configuration", [])
        old_configuration = self.old_file.get("configuration", [])
        current_param_names = {param.get("name") for param in current_configuration}
        old_param_names = {param.get("name") for param in old_configuration}
        if not old_param_names.issubset(current_param_names):
            removed_parameters = old_param_names - current_param_names
            error_message, error_code = Errors.removed_integration_parameters(
                repr(removed_parameters)
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                self.is_valid = False
                no_removed_parameter = False

        return no_removed_parameter

    @staticmethod
    def _get_field_to_required_dict(integration_json):
        """Get a dictionary field name to its required status.

        Args:
            integration_json (dict): Dictionary of the examined integration.

        Returns:
            dict. Field name to its required status.
        """
        field_to_required = {}
        configuration = integration_json.get("configuration", [])
        for field in configuration:
            field_to_required[field.get("name")] = field.get("required", False)
        return field_to_required

    @error_codes("IN147")
    def no_changed_removed_yml_fields(self):
        """checks if some specific Fields in the yml file were changed from true to false or removed
        Returns True if valid, and False otherwise.
        """
        fields = [
            "feed",
            "isfetch",
            "longRunning",
            "longRunningPort",
            "ismappable",
            "isremotesyncin",
            "isremotesyncout",
        ]
        currentscript = self.current_file.get("script", {})
        oldscript = self.old_file.get("script", {})

        removed, changed = {}, {}

        for field in fields:
            old = oldscript.get(field)
            current = currentscript.get(field)

            if (
                old is not None and old is True
            ):  # the field exists in old file and is true
                if current is None:  # the field was removed from current
                    removed[field] = old
                elif not current:  # changed from true to false
                    changed[field] = old

        if removed or changed:
            error_message, error_code = Errors.changed_integration_yml_fields(
                repr(removed), repr(changed)
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                self.is_valid = False
                return False
        return True

    @error_codes("IN116")
    def no_added_required_fields(self) -> bool:
        """Check if required field were added.
        Returns True if valid, and False otherwise.
        """
        current_field_to_required = self._get_field_to_required_dict(self.current_file)
        old_field_to_required = self._get_field_to_required_dict(self.old_file)
        no_added_required = True
        for field, required in current_field_to_required.items():
            if field in old_field_to_required.keys():
                # if required is True and old_field is False.
                if required and required != old_field_to_required[field]:
                    error_message, error_code = Errors.added_required_fields(field)
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        self.is_valid = False
                        no_added_required = False

            # if required is True but no old field.
            elif required:
                error_message, error_code = Errors.added_required_fields(field)
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    self.is_valid = False
                    no_added_required = False

        return no_added_required

    def is_id_equals_name(self):
        """Check whether the integration's ID is equal to its name

        Returns:
            bool. True if valid, and False otherwise.
        """
        return super()._is_id_equals_name("integration")

    @error_codes("IN117,IN118")
    def is_valid_display_configuration(self):
        """Validate that the display settings are not empty for non-hidden fields and for type 17 params.

        Returns:
            bool. Whether the display is there for non-hidden fields.
            Returns True if valid, and False otherwise.
        """
        configuration = self.current_file.get("configuration", [])
        for configuration_param in configuration:
            field_type = configuration_param["type"]
            is_field_hidden = configuration_param.get("hidden", False)
            configuration_display = configuration_param.get("display")

            # This parameter type will not use the display value.
            if field_type == ParameterType.EXPIRATION_FIELD.value:
                if configuration_display:
                    error_message, error_code = Errors.not_used_display_name(
                        configuration_param["name"]
                    )
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=self.structure_validator.quiet_bc,
                    ):
                        self.is_valid = False
                        return False

            elif (
                not is_field_hidden
                and not configuration_display
                and not configuration_param.get("displaypassword")
                and configuration_param["name"]
                not in ("feedExpirationPolicy", "feedExpirationInterval")
            ):
                error_message, error_code = Errors.empty_display_configuration(
                    configuration_param["name"]
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    self.is_valid = False
                    return False

        return True

    def is_docker_image_valid(self) -> bool:
        # dockers should not be checked when running on all files
        if self.skip_docker_check:
            return True
        is_iron_bank = is_iron_bank_pack(self.file_path)
        docker_image_validator = DockerImageValidator(
            self.file_path,
            is_modified_file=True,
            is_integration=True,
            ignored_errors=self.ignored_errors,
            json_file_path=self.json_file_path,
            is_iron_bank=is_iron_bank,
            specific_validations=self.specific_validations,
        )

        # making sure we don't show error of validation if fetching is failed.
        _, error_code = Errors.docker_tag_not_fetched("", "")
        if f"{self.file_path} - [{error_code}]" in FOUND_FILES_AND_ERRORS:
            return False

        if docker_image_validator.is_docker_image_valid():
            return True

        self.is_valid = False
        return False

    @error_codes("IN119")
    def is_valid_feed(self) -> bool:
        valid_from_version = valid_feed_params = True
        if self.current_file.get("script", {}).get("feed"):
            from_version = self.current_file.get(
                "fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION
            )
            if not from_version or server_version_compare("5.5.0", from_version) == 1:
                error_message, error_code = Errors.feed_wrong_from_version(from_version)
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(
                        self.file_path, "--from-version", "5.5.0"
                    ),
                ):
                    valid_from_version = False

            valid_feed_params = self.all_feed_params_exist()
        return valid_from_version and valid_feed_params

    @error_codes("IN120")
    def is_valid_pwsh(self) -> bool:
        if self.current_file.get("script", {}).get("type") == TYPE_PWSH:
            from_version = self.current_file.get(
                "fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION
            )
            if not from_version or server_version_compare("5.5.0", from_version) > 0:
                error_message, error_code = Errors.pwsh_wrong_version(from_version)
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(
                        self.file_path, "--from-version", "5.5.0"
                    ),
                ):
                    return False
        return True

    @error_codes("IN121,IN148")
    def is_valid_fetch(self) -> bool:
        """
        validate that all required fields in integration that have fetch incidents are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.current_file.get("script", {}).get("isfetch") is True:
            # get the iten marketplaces to decide which are the required params
            # if no marketplaces or xsoar in marketplaces - the required params will be INCIDENT_FETCH_REQUIRED_PARAMS (with Incident type etc. )
            # otherwise it will be the ALERT_FETCH_REQUIRED_PARAMS (with Alert type etc. )
            marketplaces = get_item_marketplaces(
                item_path=self.file_path, item_data=self.current_file
            )
            is_xsoar_marketplace = (
                not marketplaces or MarketplaceVersions.XSOAR.value in marketplaces
            )
            fetch_required_params = (
                INCIDENT_FETCH_REQUIRED_PARAMS
                if is_xsoar_marketplace
                else ALERT_FETCH_REQUIRED_PARAMS
            )
            params = [
                dict.copy(_key) for _key in self.current_file.get("configuration", [])
            ]

            # ignore optional fields
            for param in params:
                for field in param.copy():
                    if (
                        field in ["defaultvalue", "section", "advanced", "required"]
                        or ":" in field
                    ):
                        param.pop(field, None)

            for fetch_required_param in fetch_required_params:
                # If this condition returns true, we'll go over the params dict and we'll check if there's a param that match the fetch_required_param name.
                # If there is one, we know that in the params dict there is a matching param to the fetch_required_param but it has a malformed structure.
                if fetch_required_param not in params:
                    error_message = ""
                    error_code = ""
                    for param in params:
                        if param.get("name") == fetch_required_param.get("name"):
                            error_message, error_code = Errors.parameter_is_malformed(
                                fetch_required_param.get("name"),
                                yaml.dumps(fetch_required_param),
                            )
                    if not error_message:
                        error_message, error_code = Errors.parameter_missing_from_yml(
                            fetch_required_param.get("name")
                        )
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        suggested_fix=Errors.suggest_fix(self.file_path),
                    ):
                        fetch_params_exist = False

        return fetch_params_exist

    @error_codes("IN126,IN125")
    def is_valid_max_fetch_and_first_fetch(self) -> bool:
        """
        validate that the max_fetch and first_fetch params exist in the yml and the max_fetch has default value
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        fetch_params_exist = True
        if self.current_file.get("script", {}).get("isfetch") is True:
            params = self.current_file.get("configuration", [])
            first_fetch_param = None
            max_fetch_param = None
            for param in params:
                # the common names for the first_fetch param
                if param.get("name") == FIRST_FETCH:
                    first_fetch_param = param
                elif param.get("name") == MAX_FETCH:
                    max_fetch_param = param

            if not first_fetch_param:
                (
                    error_message,
                    error_code,
                ) = Errors.parameter_missing_from_yml_not_community_contributor(
                    "first_fetch", yaml.dumps(FIRST_FETCH_PARAM)
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    fetch_params_exist = False

            if not max_fetch_param:
                (
                    error_message,
                    error_code,
                ) = Errors.parameter_missing_from_yml_not_community_contributor(
                    "max_fetch", yaml.dumps(MAX_FETCH_PARAM)
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    fetch_params_exist = False

            elif not max_fetch_param.get("defaultvalue"):
                error_message, error_code = Errors.no_default_value_in_parameter(
                    "max_fetch"
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    fetch_params_exist = False

        return fetch_params_exist

    @error_codes("IN122")
    def all_feed_params_exist(self) -> bool:
        """
        validate that all required fields in feed integration are in the yml file.
        Returns:
            bool. True if the integration is defined as well False otherwise.
        """
        params_exist = True
        # Build params in efficient way of param_name: {param_field_name: param_field_value} to query quickly for param.
        params = {
            param.get("name"): {k: v for k, v in param.items()}
            for param in self.current_file.get("configuration", [])
        }
        for param_name, param_details in params.items():
            for detail in param_details.copy():
                if ":" in detail:
                    param_details.pop(detail)
            if "defaultvalue" in param_details and param_name != "feed":
                param_details.pop("defaultvalue")
            if "hidden" in param_details:
                param_details.pop("hidden")
            if "section" in param_details:
                param_details.pop("section")

        for required_param in FEED_REQUIRED_PARAMS:
            is_valid = False
            param_details = params.get(required_param.get("name"))  # type: ignore
            equal_key_values: Dict = required_param.get("must_equal", dict())  # type: ignore
            contained_key_values: Dict = required_param.get("must_contain", dict())  # type: ignore
            must_be_one_of: Dict = required_param.get("must_be_one_of", list())  # type: ignore
            if param_details:
                # Check length to see no unexpected key exists in the config. Add +1 for the 'name' key.
                is_valid = (
                    (
                        # Validate that the mentioned fields (k) are part of the parameter fields and the value is one of the options of the mentioned values (v).
                        all(
                            k in param_details and param_details[k] in v
                            for k, v in must_be_one_of.items()
                        )
                        or not must_be_one_of
                    )
                    # Validate that the mentioned fields (k) are part of the parameter fields and the value is equal the mentioned value (v).
                    and all(
                        k in param_details and param_details[k] == v
                        for k, v in equal_key_values.items()
                    )
                    # Validate that the mentioned fields (k) are part of the parameter fields and the value contains mentioned value (v).
                    and all(
                        k in param_details and v in param_details[k]
                        for k, v in contained_key_values.items()
                    )
                )
            if not is_valid:
                param_structure = dict(
                    equal_key_values,
                    **contained_key_values,
                    name=required_param.get("name"),
                )
                error_message, error_code = Errors.parameter_missing_for_feed(
                    required_param.get("name"), yaml.dumps(param_structure)
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(self.file_path),
                ):
                    params_exist = False

        return params_exist

    @error_codes("IN123")
    def is_valid_display_name(self) -> bool:
        version_number: Optional[str] = get_file_version_suffix_if_exists(
            self.current_file, check_in_display=True
        )
        if not version_number:
            return True
        else:
            display_name = self.current_file.get("display")
            correct_name = f" v{version_number}"
            if not display_name.endswith(correct_name):  # type: ignore
                error_message, error_code = Errors.invalid_version_integration_name(
                    version_number
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

            return True

    @error_codes("IN150")
    def is_valid_display_name_for_siem(self) -> bool:
        is_siem = self.current_file.get("script", {}).get("isfetchevents")

        if is_siem:
            display_name = self.current_file.get("display", "")
            if not display_name.endswith("Event Collector"):
                error_message, error_code = Errors.invalid_siem_integration_name(
                    display_name
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    def _is_replaced_by_type9(self, display_name: str) -> bool:
        """
        This function is used to check the case where a parameter is hidden but because is replaced by a type 9 parameter.
        Returns:
            bool. True if the parameter is hidden but because is replaced by a type 9 parameter. False otherwise.
        """
        for param in self.current_file.get("configuration", ()):
            if param.get("type") == 9 and display_name.lower() in (
                param.get("display", "").lower(),
                param.get("displaypassword", "").lower(),
            ):
                return True
        return False

    @error_codes("IN124,IN156")
    def is_valid_hidden_params(self) -> bool:
        """
        Verify there are no non-allowed hidden integration parameters.
        This is a workaround as pykwalify schemas do not allow multiple types
         (e.g. equivalent for Union[list[str] | bool]).

        See update_hidden_parameters_value for the allowed values the hidden attribute.

        Returns:
            bool. True if there aren't non-allowed hidden parameters. False otherwise.
        """
        valid = True

        for param in self.current_file.get("configuration", ()):
            name = param.get("name", "")
            display_name = param.get("display", "")
            type_ = param.get("type")
            hidden = param.get("hidden")

            invalid_type = not isinstance(hidden, (type(None), bool, list, str))
            invalid_string = isinstance(hidden, str) and not is_str_bool(hidden)

            if invalid_type or invalid_string:
                message, code = Errors.invalid_hidden_attribute_for_param(name, hidden)
                if self.handle_error(message, code, self.file_path):
                    valid = False

            is_true = (hidden is True) or (
                is_str_bool(hidden) and string_to_bool(hidden)
            )
            invalid_bool = is_true and name not in ALLOWED_HIDDEN_PARAMS
            hidden_in_all_marketplaces = isinstance(hidden, list) and set(
                hidden
            ) == set(MarketplaceVersions)

            if invalid_bool or hidden_in_all_marketplaces:
                if type_ in (0, 4, 12, 14) and self._is_replaced_by_type9(display_name):
                    continue
                error_message, error_code = Errors.param_not_allowed_to_hide(name)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    valid = False

            elif isinstance(hidden, list) and (
                invalid := set(hidden).difference(MarketplaceVersions)
            ):
                # if the value is a list, all its values must be marketplace names
                joined_marketplaces = ", ".join(map(str, invalid))
                message, code = Errors.invalid_hidden_attribute_for_param(
                    name, joined_marketplaces
                )
                if self.handle_error(message, code, self.file_path):
                    valid = False

        return valid

    def is_valid_image(self) -> bool:
        """Verifies integration image/logo is valid.

        Returns:
            bool. True if integration image/logo is valid, False otherwise.
        """
        image_validator = ImageValidator(
            self.file_path,
            ignored_errors=self.ignored_errors,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        if not image_validator.is_valid():
            return False
        return True

    def is_valid_description(self, beta_integration: bool = False) -> bool:
        """Verifies integration description is valid.

        Returns:
            bool: True if description is valid, False otherwise.
        """
        description_validator = DescriptionValidator(
            self.file_path,
            ignored_errors=self.ignored_errors,
            json_file_path=self.json_file_path,
            specific_validations=self.specific_validations,
        )
        if beta_integration:
            if not description_validator.is_valid_beta_description():
                return False
        else:
            if not description_validator.is_valid_file():
                return False
        return True

    @error_codes("IN130")
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
        script = self.current_file.get("script", {})

        if not any(
            [
                script.get("commands"),
                script.get("isfetch", script.get("isFetch")),
                script.get("feed"),
                script.get("longRunning"),
            ]
        ):
            self.is_valid = False
            error, code = Errors.integration_not_runnable()
            self.handle_error(error, code, file_path=self.file_path)
            return False
        return True

    @error_codes("IN135")
    def is_valid_parameters_display_name(self) -> bool:
        """Verifies integration parameters display name is valid.

        Returns:
            bool: True if description is valid - capitalized and spaced using whitespace and not underscores,
            False otherwise.
        """
        configuration = self.current_file.get("configuration", {})
        parameters_display_name = [
            param.get("display") for param in configuration if param.get("display")
        ]

        invalid_display_names = []
        for parameter in parameters_display_name:
            invalid_display_names.append(parameter) if parameter and not parameter[
                0
            ].isupper() or "_" in parameter else None

        if invalid_display_names:
            (
                error_message,
                error_code,
            ) = Errors.invalid_integration_parameters_display_name(
                invalid_display_names
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @error_codes("IN153")
    def is_valid_parameter_url_default_value(self) -> bool:
        """Verifies integration parameters default value is valid.

        Returns:
            bool: True if the default value of the url parameter uses the https protocol,
            False otherwise.
        """
        configuration = self.current_file.get("configuration", {})
        parameters_default_values = [
            (param.get("display"), param.get("defaultvalue"))
            for param in configuration
            if param.get("defaultvalue")
        ]

        is_valid = True
        for param, defaultvalue in parameters_default_values:
            if defaultvalue and isinstance(defaultvalue, str):
                if defaultvalue.startswith("http:"):
                    (
                        error_message,
                        error_code,
                    ) = Errors.not_supported_integration_parameter_url_defaultvalue(
                        param, defaultvalue
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        is_valid = False

        return is_valid

    @error_codes("IN138,IN137")
    def is_valid_integration_file_path(self) -> bool:
        absolute_file_path = Path(self.file_path)
        integrations_folder = absolute_file_path.parent.name

        # drop file extension
        integration_file = Path(absolute_file_path.name).stem

        if integrations_folder == "Integrations":
            if not integration_file.startswith("integration-"):
                (
                    error_message,
                    error_code,
                ) = Errors.is_valid_integration_file_path_in_integrations_folder(
                    integration_file
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        elif integration_file != integrations_folder:
            valid_integration_name = integration_file.replace("-", "").replace("_", "")

            if valid_integration_name != integrations_folder:
                (
                    error_message,
                    error_code,
                ) = Errors.is_valid_integration_file_path_in_folder(integration_file)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    @error_codes("IN137")
    def is_valid_py_file_names(self):
        # Files that will be excluded from the check.
        excluded_files = [
            "demistomock.py",
            "conftest.py",
            "CommonServerPython.py",
            "CommonServerUserPython.py",
            ".vulture_whitelist.py",
        ]

        # Files that will be excluded from the check if they end with the given suffix (str.endswith).
        excluded_file_suffixes = [
            "ApiModule.py",  # won't affect the actual API module since it's a script not an integration.
        ]

        # Gets the all integration .py files from the integration folder.
        files_to_check = get_files_in_dir(
            os.path.dirname(self.file_path), ["py"], False
        )
        invalid_files = []
        integrations_folder = Path(os.path.dirname(self.file_path)).name

        for file_path in files_to_check:
            file_name = Path(file_path).name

            # If the file is in an exclusion list, skip it.
            if file_name in excluded_files or any(
                file_name.endswith(suffix) for suffix in excluded_file_suffixes
            ):
                continue

            # The unittest has _test.py suffix whereas the integration only has the .py suffix
            splitter = "_" if file_name.endswith("_test.py") else "."
            base_name = file_name.rsplit(splitter, 1)[0]

            if integrations_folder != base_name:
                invalid_files.append(file_name)

        if invalid_files:
            error_message, error_code = Errors.is_valid_integration_file_path_in_folder(
                invalid_files
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    @error_codes("IN131")
    def is_mapping_fields_command_exist(self) -> bool:
        """
        Check if get-mapping-fields command exists in the YML if  the ismappble field is set to true
        Returns:
            True if get-mapping-fields commands exist in the yml, else False.
        """
        script = self.current_file.get("script", {})
        if script.get("ismappable"):
            command_names = {command["name"] for command in script.get("commands", [])}
            if "get-mapping-fields" not in command_names:
                error, code = Errors.missing_get_mapping_fields_command()
                if self.handle_error(error, code, file_path=self.file_path):
                    self.is_valid = False
                    return False
        return True

    @error_codes("RM102,IN136")
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
        if not Path(dir_path, "README.md").exists():
            return True

        # Only run validation if the validation has not run with is_context_different_in_yml on readme
        # so no duplicates errors will be created:
        error, missing_from_readme_error_code = Errors.readme_missing_output_context(
            "", ""
        )
        error, missing_from_yml_error_code = Errors.missing_output_context("", "")
        readme_path = os.path.join(dir_path, "README.md")

        if (
            f"{readme_path} - [{missing_from_readme_error_code}]"
            in FOUND_FILES_AND_IGNORED_ERRORS
            or f"{readme_path} - [{missing_from_readme_error_code}]"
            in FOUND_FILES_AND_ERRORS
            or f"{self.file_path} - [{missing_from_yml_error_code}]"
            in FOUND_FILES_AND_IGNORED_ERRORS
            or f"{self.file_path} - [{missing_from_yml_error_code}]"
            in FOUND_FILES_AND_ERRORS
        ):
            return False

        # get README file's content
        with open(readme_path) as readme:
            readme_content = readme.read()

        # commands = self.current_file.get("script", {}).get('commands', [])
        difference = compare_context_path_in_yml_and_readme(
            self.current_file, readme_content
        )
        for command_name in difference:
            if difference[command_name].get("only in yml"):
                error, code = Errors.readme_missing_output_context(
                    command_name, ", ".join(difference[command_name].get("only in yml"))
                )
                if self.handle_error(error, code, file_path=readme_path):
                    valid = False

            if difference[command_name].get("only in readme"):
                error, code = Errors.missing_output_context(
                    command_name,
                    ", ".join(difference[command_name].get("only in readme")),
                )
                if self.handle_error(error, code, file_path=self.file_path):
                    valid = False

        return valid

    def is_there_separators_in_names(self) -> bool:
        """
        Check if there are separators in the integration folder or files.

        Returns:
            true if the folder/files names are valid and there are no separators, and false if not.
        """
        is_unified_integration = self.current_file.get("script", {}).get(
            "script", ""
        ) not in ["-", ""]

        if is_unified_integration:
            return True

        answers = [self.check_separators_in_folder(), self.check_separators_in_files()]

        return all(answers)

    @error_codes("BA108")
    def check_separators_in_folder(self) -> bool:
        """
        Check if there are separators in the integration folder.

        Returns:
            true if the name is valid and there are no separators, and false if not.
        """

        integration_folder_name = Path(os.path.dirname(self.file_path)).name
        valid_folder_name = self.remove_separators_from_name(integration_folder_name)

        if valid_folder_name != integration_folder_name:
            error_message, error_code = Errors.folder_name_has_separators(
                "integration", integration_folder_name, valid_folder_name
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    @error_codes("BA109")
    def check_separators_in_files(self):
        """
        Check if there are separators in the integration files names.

        Returns:
            true if the files names are valid and there is no separators, and false if not.
        """

        # Gets the all integration files that may have the integration name as base name
        files_to_check = get_files_in_dir(
            os.path.dirname(self.file_path), ["yml", "py", "md", "png"], False
        )
        invalid_files = []
        valid_files = []

        for file_path in files_to_check:
            if (file_name := Path(file_path).name).startswith("README"):
                continue

            if (
                file_name.endswith("_image.png")
                or file_name.endswith("_description.md")
                or file_name.endswith("_test.py")
                or file_name.endswith("_unified.yml")
            ):
                base_name = file_name.rsplit("_", 1)[0]

            else:
                base_name = file_name.rsplit(".", 1)[0]

            valid_base_name = self.remove_separators_from_name(base_name)

            if valid_base_name != base_name:
                invalid_files.append(file_name)
                valid_files.append(valid_base_name.join(file_name.rsplit(base_name, 1)))

        if invalid_files:
            error_message, error_code = Errors.file_name_has_separators(
                "integration", invalid_files, valid_files
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    @error_codes("BA110")
    def name_not_contain_the_type(self):
        """
        Check that the entity name or display name does not contain the entity type
        Returns: True if the name is valid
        """

        name = self.current_file.get("name", "")
        display_name = self.current_file.get("display", "")
        field_names = []
        if "integration" in name.lower():
            field_names.append("name")
        if "integration" in display_name.lower():
            field_names.append("display")

        if field_names:
            error_message, error_code = Errors.field_contain_forbidden_word(
                field_names=field_names, word="integration"
            )

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
        commands = self.current_file.get("script", {}).get("commands", [])

        if "endpoint" not in [x.get("name") for x in commands]:
            return True

        # extracting the specific command from commands.
        endpoint_command = [arg for arg in commands if arg.get("name") == "endpoint"][0]
        return self._is_valid_endpoint_inputs(
            endpoint_command, required_arguments=ENDPOINT_FLEXIBLE_REQUIRED_ARGS
        )

    @error_codes("IN141,IN105")
    def _is_valid_endpoint_inputs(self, command_data, required_arguments):
        """
        Check if the input for endpoint commands includes at least one required_arguments,
        and that only ip is the default argument.
        Returns:
            true if the inputs are valid.
        """
        endpoint_command_inputs = command_data.get("arguments", [])
        existing_arguments = {arg["name"] for arg in endpoint_command_inputs}

        # checking at least one of the required argument is found as argument
        if not set(required_arguments).intersection(existing_arguments):
            error_message, error_code = Errors.reputation_missing_argument(
                list(required_arguments), command_data.get("name"), all=False
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        # checking no other arguments are default argument:
        default_args_found = [
            (arg.get("name"), arg.get("default", False))
            for arg in endpoint_command_inputs
        ]
        command_default_arg_map = BANG_COMMAND_ARGS_MAPPING_DICT[ENDPOINT_COMMAND_NAME]
        default_arg_name = command_default_arg_map["default"]
        other_default_args_found = list(
            filter(
                lambda x: x[1] is True and x[0] not in default_arg_name,
                default_args_found,
            )
        )
        if other_default_args_found:
            error_message, error_code = Errors.wrong_default_argument(
                default_arg_name, ENDPOINT_COMMAND_NAME
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

    @error_codes("IN142,IN143")
    def default_params_have_default_additional_info(self):
        """Check if the all integration params that can have a default description have a it set.
        Raises warnings if the additional info is defined (not empty) but is different from the default.

        Returns:
            bool: True if all relevant params have an additional info value
                  False if at least one param that can have a default additionalInfo has an empty one.
        """
        params_missing_defaults = []
        params_with_non_default_description = []

        additional_info = {
            param["name"]: param.get("additionalinfo", "")
            for param in self.current_file.get("configuration", [])
        }

        for param, info in additional_info.items():
            if (
                param in default_additional_info
                and info != default_additional_info[param]
            ):
                if not info:
                    params_missing_defaults.append(param)
                else:
                    params_with_non_default_description.append(param)
        if params_with_non_default_description:
            (
                non_default_error_message,
                non_default_error_code,
            ) = Errors.non_default_additional_info(params_with_non_default_description)
            self.handle_error(
                non_default_error_message,
                non_default_error_code,
                file_path=self.file_path,
                warning=True,
            )

        if params_missing_defaults:
            (
                missing_error_message,
                missing_error_code,
            ) = Errors.missing_default_additional_info(params_missing_defaults)
            self.handle_error(
                missing_error_message,
                missing_error_code,
                self.current_file,
                suggested_fix=Errors.suggest_fix(self.file_path),
            )
            return False
        return True

    @error_codes("IN146")
    def has_no_fromlicense_key_in_contributions_integration(self):
        """Verifies that only xsoar supported integration can contain the `fromlicense` key in the configuration.

        Returns:
            bool: True if the key does not exist or if the support level of the integration is `xsoar`, False otherwise.
        """
        pack_name = get_pack_name(self.file_path)
        if pack_name:
            metadata_path = Path(PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME)
            metadata_content = self.get_metadata_file_content(metadata_path)

            if metadata_content.get("support", "").lower() == XSOAR_SUPPORT:
                return True

            conf_params = self.current_file.get("configuration", [])
            for param_name in conf_params:
                if "fromlicense" in param_name.keys():
                    error_message, error_code = Errors.fromlicense_in_parameters(
                        param_name.get("name")
                    )

                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        self.is_valid = False
                        return False

            return True

        else:
            raise Exception(
                "Could not find the pack name of the integration, "
                "please verify the integration is in a pack"
            )

    @error_codes("IN145")
    def is_api_token_in_credential_type(self):
        """Checks if there are no keys with the `encrypted` type,
            The best practice is to use the `credential` type instead of `encrypted`.

        Returns:
            bool: True if there is no a key with type encrypted False otherwise.
        """
        pack_name = get_pack_name(self.file_path)
        if pack_name:
            metadata_path = Path(PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME)
            metadata_content = self.get_metadata_file_content(metadata_path)

            if metadata_content.get("support") != XSOAR_SUPPORT:
                return True

        conf_params = self.current_file.get("configuration", [])
        for param in conf_params:
            if param.get("type") == 4 and not param.get("hidden"):
                (
                    error_message,
                    error_code,
                ) = Errors.api_token_is_not_in_credential_type(param.get("name"))
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    @error_codes("IN149")
    def are_common_outputs_with_description(self):
        defaults = get_default_output_description()

        missing = {}
        for command in self.current_file.get("script", {}).get("commands", []):
            command_missing = []
            for output in command.get("outputs") or []:  # outputs in some UT are None
                if output["contextPath"] in defaults and not output.get("description"):
                    command_missing.append(output["contextPath"])

            if command_missing:
                missing[command["name"]] = command_missing

        if missing:
            error_message, error_code = Errors.empty_outputs_common_paths(
                missing, self.file_path
            )
            if self.handle_error(error_message, error_code, self.file_path):
                return False

        return True

    def exclude_get_indicators_commands(self, missing_commands_from_readme):
        """
        Delete the get-indicators commands from the command list
        Args:
            missing_commands_from_readme (list): a list of all the captured missing from readme commands.

        Return:
            list: A list with the same commands as the given list except for the get-indicators commands.
        """
        return [
            missing_command
            for missing_command in missing_commands_from_readme
            if not missing_command.endswith("get-indicators")
        ]

    @error_codes("RM110")
    def verify_yml_commands_match_readme(self, is_modified=False):
        """
        Checks if there are commands that doesn't appear in the readme but appear in the .yml file
        Args:
            is_modified (bool): Whether the given files are modified or not.

        Return:
            bool: True if all commands are documented in the README, False if there's no README file in the expected
             path, or any of the commands is missing.
        """
        if not is_modified:
            return True
        yml_commands_list = extract_none_deprecated_command_names_from_yml(
            self.current_file
        )
        is_valid = True
        readme_path = Path(self.file_path).parent / "README.md"
        if not readme_path.exists():
            return False

        readme_content = readme_path.read_text()
        excluded_from_readme_commands = [
            "get-mapping-fields",
            "xsoar-search-incidents",
            "xsoar-get-incident",
            "get-remote-data",
            "update-remote-data",
            "get-modified-remote-data",
            "update-remote-system",
        ]
        missing_commands_from_readme = [
            command
            for command in yml_commands_list
            if command not in readme_content
            and command not in excluded_from_readme_commands
        ]
        missing_commands_from_readme = self.exclude_get_indicators_commands(
            missing_commands_from_readme
        )
        if missing_commands_from_readme:
            error_message, error_code = Errors.missing_commands_from_readme(
                Path(self.file_path).name, missing_commands_from_readme
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @error_codes("IN154")
    def verify_reputation_commands_has_reliability(self):
        """
        If the integration is a feed, or has reputation commands, assure it has a reliability configuration parameter.

        Return:
            bool: True if there are no reputation commands or there is a reliability parameter
             and False if there is at least one reputation command without a reliability parameter in the configuration.
        """
        yml_config_names = [
            config_item["name"].casefold()
            for config_item in self.current_file.get("configuration", {})
            if config_item.get("name")
        ]

        # Integration has a reliability parameter
        if any(
            reliability_parameter_name.casefold() in yml_config_names
            for reliability_parameter_name in RELIABILITY_PARAMETER_NAMES
        ):
            return True

        # Integration doesn't have a reliability parameter
        if bool(
            self.current_file.get("script", {}).get("feed")
        ):  # Is a feed integration
            error_message, error_code = Errors.missing_reliability_parameter(
                is_feed=True
            )

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        else:
            commands_names = [
                command.get("name")
                for command in self.current_file.get("script", {}).get("commands", [])
            ]

            for command in commands_names:
                if (
                    command in REPUTATION_COMMAND_NAMES
                ):  # Integration has a reputation command
                    (error_message, error_code,) = Errors.missing_reliability_parameter(
                        is_feed=False, command_name=command
                    )

                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        return False

        return True

    @error_codes("IN155")
    def is_integration_deprecated_and_used(self):
        """
        Checks if there are commands that are deprecated and is used in other none-deprcated scripts / playbooks.

        Return:
            bool: False if there are deprecated commands that are used in any none-deprcated scripts / playbooks.
            True otherwise.
        """
        deprecated_commands_list = []
        is_valid = True

        if self.current_file.get("deprecated"):
            deprecated_commands_list = [
                command.get("name")
                for command in self.current_file.get("script", {}).get("commands", [])
            ]
        else:
            deprecated_commands_list = extract_deprecated_command_names_from_yml(
                self.current_file
            )

        if deprecated_commands_list:
            integration_id = self.current_file.get("commonfields", {}).get("id", "")
            used_commands_dict = (
                self.deprecation_validator.validate_integartion_commands_deprecation(
                    deprecated_commands_list, integration_id
                )
            )
            if used_commands_dict:
                error_message, error_code = Errors.integration_is_deprecated_and_used(
                    self.current_file.get("name"), used_commands_dict
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    is_valid = False

        return is_valid

    def get_test_path(self, file_path: str):
        """Gets a yml path and returns the matching integration's test."""
        test_path = Path(file_path)
        test_file_name = test_path.parts[-1].replace(".yml", "_test.py")
        return test_path.parent / test_file_name

    def has_unittest(self, file_path):
        """Checks if the tests file exist. If so, Test Playbook is not a must."""
        test_path = self.get_test_path(file_path)

        # We only check existence as we have coverage report to check the actual tests
        if not test_path.exists():
            return False

        return True

    @error_codes("IN157")
    def is_native_image_does_not_exist_in_yml(self):
        if self.current_file.get("script", {}).get("nativeimage"):
            error_message, error_code = Errors.nativeimage_exist_in_integration_yml(
                self.current_file.get("commonfields", {}).get("id")
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IN161")
    def is_valid_xsiam_marketplace(self):
        """Checks if XSIAM integration has only the marketplacev2 entry"""
        is_siem = self.current_file.get("script", {}).get("isfetchevents")
        marketplaces = self.current_file.get("marketplaces", [])
        if is_siem:
            # Should have only marketplacev2 entry
            if not len(marketplaces) == 1 or "marketplacev2" not in marketplaces:
                error_message, error_code = Errors.invalid_siem_marketplaces_entry()
                if self.handle_error(error_message, error_code, self.file_path):
                    return False

        return True

    @error_codes("IN162")
    def is_partner_collector_has_xsoar_support_level_header(self) -> bool:
        """
        Validates that event collectors under partner supported packs always has the supportlevelheader = xsoar key:value.
        """
        if (script := (self.current_file.get("script") or {})) and (
            script.get("isfetchevents") or script.get("isfetcheventsandassets")
        ):
            pack_name = get_pack_name(self.file_path)
            if pack_name:
                metadata_path = Path(PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME)
                metadata_content = self.get_metadata_file_content(metadata_path)

                support_level_header = self.current_file.get(SUPPORT_LEVEL_HEADER)
                if (
                    metadata_content.get("support", "").lower() == PARTNER_SUPPORT
                    and support_level_header != XSOAR_SUPPORT
                ):
                    (
                        error_message,
                        error_code,
                    ) = Errors.partner_collector_does_not_have_xsoar_support_level(
                        self.file_path
                    )
                    if self.handle_error(error_message, error_code, self.file_path):
                        return False
        return True

    @error_codes("DS108")
    def is_line_ends_with_dot(self):
        lines_with_missing_dot = ""
        if self.running_validations_using_git:
            for command in self.current_file.get("script", {}).get("commands", []):
                current_command = super().is_line_ends_with_dot(command, "arguments")
                if current_command:
                    lines_with_missing_dot += (
                        f"- In command {command.get('name')}:\n{current_command}"
                    )
            stripped_description = strip_description(
                self.current_file.get("description", "")
            )

            if super().is_invalid_description_sentence(stripped_description):
                lines_with_missing_dot += "The file's description field is missing a '.' in the end of the sentence."
            if lines_with_missing_dot:
                error_message, error_code = Errors.description_missing_dot_at_the_end(
                    lines_with_missing_dot
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(self.file_path),
                ):
                    return False
        return True
