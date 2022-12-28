from pathlib import Path
from typing import Tuple

import click

from demisto_sdk.commands.common.constants import (
    ALERT_FETCH_REQUIRED_PARAMS,
    BANG_COMMAND_NAMES,
    BETA_INTEGRATION,
    FEED_REQUIRED_PARAMS,
    INCIDENT_FETCH_REQUIRED_PARAMS,
    INTEGRATION,
    TYPE_PWSH,
    MarketplaceVersions,
    ParameterType,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import find_type, get_item_marketplaces, get_json
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_script import ScriptYMLFormat

json = JSON_Handler()


class IntegrationYMLFormat(BaseUpdateYML):
    """IntegrationYMLFormat class is designed to update integration YML file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
    """

    ARGUMENTS_DESCRIPTION = {
        "insecure": "Trust any certificate (not secure)",
        "unsecure": "Trust any certificate (not secure)",
        "proxy": "Use system proxy settings",
    }

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        verbose: bool = False,
        update_docker: bool = False,
        add_tests: bool = False,
        clear_cache: bool = False,
        **kwargs,
    ):
        super().__init__(
            input,
            output,
            path,
            from_version,
            no_validate,
            verbose=verbose,
            add_tests=add_tests,
            clear_cache=clear_cache,
            **kwargs,
        )
        self.update_docker = update_docker
        if not from_version and self.data.get("script", {}).get("type") == TYPE_PWSH:
            self.from_version = "5.5.0"
        self.is_beta = False
        integration_type = find_type(input, clear_cache=clear_cache)
        if integration_type:
            self.is_beta = find_type(input).value == "betaintegration"

    def update_proxy_insecure_param_to_default(self):
        """Updates important integration arguments names and description."""
        if self.verbose:
            click.echo(
                "Updating proxy and insecure/unsecure integration arguments description to default"
            )

        for integration_argument in self.data.get("configuration", {}):
            argument_name = integration_argument.get("name", "")

            if argument_name in self.ARGUMENTS_DESCRIPTION:
                integration_argument["display"] = self.ARGUMENTS_DESCRIPTION[
                    argument_name
                ]
                if integration_argument.get("required", False):
                    integration_argument["required"] = False
                integration_argument["type"] = 8

    def set_params_default_additional_info(self):
        from demisto_sdk.commands.common.default_additional_info_loader import (
            load_default_additional_info_dict,
        )

        default_additional_info = load_default_additional_info_dict()

        if self.verbose:
            click.echo(
                "Updating params with an empty additionalnifo, to the default (if exists)"
            )

        for param in self.data.get("configuration", {}):
            if param["name"] in default_additional_info and not param.get(
                "additionalinfo"
            ):
                param["additionalinfo"] = default_additional_info[param["name"]]

    def set_default_outputs(self):
        """Replaces empty output descriptions with default values"""
        if not self.data:
            return

        default_values = get_json(
            Path(__file__).absolute().parents[3] / "demisto_sdk/commands/common/"
            "default_output_descriptions.json"
        )

        if self.verbose:
            click.echo(
                "Updating empty integration outputs to their default (if exists)"
            )

        for command in self.data.get("script", {}).get("commands", {}):
            for output in command.get("outputs", []):
                if (
                    output["contextPath"] in default_values
                    and output.get("description") == ""
                ):  # could be missing -> None
                    output["description"] = default_values[output["contextPath"]]

    def set_reputation_commands_basic_argument_as_needed(self):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        if self.verbose:
            click.echo(
                "Updating reputation commands' basic arguments to be True for default, isArray and required"
            )

        integration_commands = self.data.get("script", {}).get("commands", [])

        for command in integration_commands:
            command_name = command.get("name", "")

            if command_name in BANG_COMMAND_NAMES:
                for argument in command.get(
                    "arguments", []
                ):  # If there're arguments under the command
                    name = argument.get("name")
                    if name == command_name:
                        is_array = argument.get("isArray", False)
                        if not is_array:
                            click.echo(
                                f"isArray field in {name} command is set to False. Fix the command to support that function and set it to True."
                            )
                        argument.update(
                            {"default": True, "isArray": is_array, "required": True}
                        )
                        break
                else:  # No arguments at all
                    default_bang_args = {
                        "default": True,
                        "description": "",
                        "isArray": True,
                        "name": command_name,
                        "required": True,
                        "secret": False,
                    }
                    click.echo(
                        f"Command {command_name} has no arguemnts. Setting them: {json.dumps(default_bang_args, indent=4)}"
                    )
                    argument_list: list = command.get("arguments", [])
                    argument_list.append(default_bang_args)
                    command["arguments"] = argument_list

    def set_fetch_params_in_config(self):
        """
        Check if the data is of fetch integration and if so, check that isfetch and incidenttype exist with the
        correct fields.
        """
        if self.data.get("script", {}).get("isfetch") is True:
            # Creates a deep copy of the feed integration configuration so the 'defaultvalue` field would not get
            # popped from the original configuration params.
            params = [dict(config) for config in self.data.get("configuration", [])]

            # ignore optional fields
            for param in params:
                for field in ("defaultvalue", "section", "advanced"):
                    param.pop(field, None)

            # get the iten marketplaces to decide which are the required params
            # if no marketplaces or xsoar in marketplaces - the required params will be INCIDENT_FETCH_REQUIRED_PARAMS (with Incident type etc. )
            # otherwise it will be the ALERT_FETCH_REQUIRED_PARAMS (with Alert type etc. )
            marketplaces = get_item_marketplaces(
                item_path=self.source_file, item_data=self.data
            )
            is_xsoar_marketplace = (
                not marketplaces or MarketplaceVersions.XSOAR.value in marketplaces
            )
            fetch_required_params, params_to_remove = (
                (INCIDENT_FETCH_REQUIRED_PARAMS, ALERT_FETCH_REQUIRED_PARAMS)
                if is_xsoar_marketplace
                else (ALERT_FETCH_REQUIRED_PARAMS, INCIDENT_FETCH_REQUIRED_PARAMS)
            )

            for param_to_add, param_to_remove in zip(
                fetch_required_params, params_to_remove
            ):
                if param_to_add not in params:
                    self.data["configuration"].append(param_to_add)
                if param_to_remove in params:
                    self.data["configuration"].remove(param_to_remove)

    def set_feed_params_in_config(self):
        """
        format the feed integration yml so all required fields in feed integration will exist in the yml file.
        """
        if self.data.get("script", {}).get("feed"):
            # Creates a deep copy of the feed integration configuration so the 'defaultvalue` field would not get
            # popped from the original configuration params.
            params = [dict(config) for config in self.data.get("configuration", [])]
            param_names = {param.get("name") for param in params if "name" in param}
            for counter, param in enumerate(params):
                if "defaultvalue" in param and param.get("name") != "feed":
                    params[counter].pop("defaultvalue")
            for param_details in FEED_REQUIRED_PARAMS:
                param = {"name": param_details.get("name")}
                param.update(param_details.get("must_equal", dict()))  # type: ignore
                param.update(param_details.get("must_contain", dict()))  # type: ignore
                if param.get("name") not in param_names:
                    self.data["configuration"].append(param)

    def update_docker_image(self):
        if self.update_docker:
            ScriptYMLFormat.update_docker_image_in_script(
                self.data["script"],
                self.source_file,
                self.data.get(self.from_version_key),
            )

    def update_beta_integration(self):
        self.data["display"] = self.data["name"] + " (Beta)"
        self.data["beta"] = True

    def set_default_value_for_checkbox(self):
        """Check the boolean default value are true or false lowercase"""
        config = self.data.get("configuration", {})
        for param in config:
            if param.get("type") == ParameterType.BOOLEAN.value:
                value = param.get("defaultvalue")
                if value not in ("true", "false"):
                    if "true" == str(value).lower():
                        param["defaultvalue"] = "true"
                    elif "false" == str(value).lower():
                        param["defaultvalue"] = "false"

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n================= Updating file {self.source_file} =================",
                fg="bright_blue",
            )
            super().update_yml(
                file_type=BETA_INTEGRATION if self.is_beta else INTEGRATION
            )
            self.update_tests()
            self.update_conf_json("integration")
            self.update_proxy_insecure_param_to_default()
            self.set_params_default_additional_info()
            self.set_reputation_commands_basic_argument_as_needed()
            self.set_default_outputs()
            self.set_fetch_params_in_config()
            self.set_feed_params_in_config()
            self.update_docker_image()
            self.set_default_value_for_checkbox()

            if self.is_beta:
                self.update_beta_integration()

            self.save_yml_to_destination_file()

            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()
