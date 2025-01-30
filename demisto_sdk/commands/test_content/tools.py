import ast
import logging  # noqa: TID251 # specific case, passed as argument to 3rd party
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from pprint import pformat
from subprocess import STDOUT, CalledProcessError, check_output
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import demisto_client
import pytz
import requests
import typer
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import parse_int_or_default
from demisto_sdk.commands.test_content.constants import SSH_USER
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_client import XsiamApiClient

XSIAM_CLIENT_SLEEP_INTERVAL = 60
XSIAM_CLIENT_RETRY_ATTEMPTS = 5


def update_server_configuration(
    client: demisto_client,
    server_configuration: Optional[Dict],
    error_msg: str,
    logging_manager=logger,
    config_keys_to_delete: Optional[Set[str]] = None,
):
    """updates server configuration

    Args:
        client (demisto_client): The configured client to use.
        server_configuration (dict): The server configuration to be added
        error_msg (str): The error message
        config_keys_to_delete (set): The server configuration keys to be deleted

    Returns:
        response_data: The response data
        status_code: The response status code
        prev_system_conf: Previous stored system conf
    """
    system_conf_response = demisto_client.generic_request_func(
        self=client, path="/system/config", method="GET"
    )
    system_conf = ast.literal_eval(system_conf_response[0]).get("sysConf", {})
    logging_manager.debug(f"Current server configurations are {pformat(system_conf)}")

    prev_system_conf = deepcopy(system_conf)

    if config_keys_to_delete:
        for key in config_keys_to_delete:
            system_conf.pop(key, None)

    if server_configuration:
        system_conf.update(server_configuration)

    data = {"data": system_conf, "version": -1}
    response_data, status_code, _ = demisto_client.generic_request_func(
        self=client, path="/system/config", method="POST", body=data
    )

    logging_manager.debug(f"Updating server configurations with {pformat(system_conf)}")

    try:
        result_object = ast.literal_eval(response_data)
        logging_manager.debug(
            f"Updated server configurations with response: {pformat(result_object)}"
        )
    except ValueError as err:
        logging_manager.exception(
            f"failed to parse response from demisto. response is {response_data}.\nError:\n{err}"
        )
        return

    if status_code >= 300 or status_code < 200:
        message = result_object.get("message", "")
        logging_manager.error(f"{error_msg} {status_code}\n{message}")
    return response_data, status_code, prev_system_conf


def is_redhat_instance(instance_ip: str) -> bool:
    """
    As part of the AMI creation - in case the AMI is RHEL a file named '/home/gcp-user/rhel_ami' is created as
    an indication.
    If not
    Args:
        instance_ip: The instance IP to check.

    Returns:
        True if the file '/home/gcp-user/rhel_ami' exists on the instance, else False
    """
    try:
        check_output(
            f"ssh {SSH_USER}@{instance_ip} ls -l /home/ec2-user/rhel_ami".split(),
            stderr=STDOUT,
        )
        return True
    except CalledProcessError:
        return False


def get_ui_url(client_host):
    """

    Args:
        client_host: the client host

    Returns: the UI URL of the server. For XSIAM we remove the 'api-' prefix to get the UI URL of the server,
    whereas for XSOAR it will remain the same (the UI URL is the same).

    """
    return client_host.replace("https://api-", "https://")


# ================= Methods and Classes used in modeling rules and playbook flow commands ================= #


def get_utc_now() -> datetime:
    """Get the current time in UTC, with timezone aware."""
    return datetime.now(tz=pytz.UTC)


def duration_since_start_time(start_time: datetime) -> float:
    """Get the duration since the given start time, in seconds.

    Args:
        start_time (datetime): Start time.

    Returns:
        float: Duration since the given start time, in seconds.
    """
    return (get_utc_now() - start_time).total_seconds()


def day_suffix(day: int) -> str:
    """
    Returns a suffix string base on the day of the month.
        for 1, 21, 31 => st
        for 2, 22 => nd
        for 3, 23 => rd
        for to all the others => th

        see here for more details: https://en.wikipedia.org/wiki/English_numerals#Ordinal_numbers

    Args:
        day: The day of the month represented by a number.

    Returns:
        suffix string (st, nd, rd, th).
    """
    return "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def get_relative_path_to_content(path: Path) -> str:
    """Get the relative path to the content directory.

    Args:
        path: The path to the content item.

    Returns:
        Path: The relative path to the content directory.
    """
    if path.is_absolute() and path.as_posix().startswith(CONTENT_PATH.as_posix()):
        return path.as_posix().replace(f"{CONTENT_PATH.as_posix()}{os.path.sep}", "")
    return path.as_posix()


def get_type_pretty_name(obj: Any) -> str:
    """Get the pretty name of the type of the given object.

    Args:
        obj (Any): The object to get the type name for.

    Returns:
        str: The pretty name of the type of the given object.
    """
    return {
        type(None): "null",
        list: "list",
        dict: "dict",
        tuple: "tuple",
        set: "set",
        UUID: "UUID",
        str: "string",
        int: "int",
        float: "float",
        bool: "boolean",
        datetime: "datetime",
    }.get(type(obj), str(type(obj)))


def create_retrying_caller(retry_attempts: int, sleep_interval: int) -> Retrying:
    """Create a Retrying object with the given retry_attempts and sleep_interval."""
    sleep_interval = parse_int_or_default(sleep_interval, XSIAM_CLIENT_SLEEP_INTERVAL)
    retry_attempts = parse_int_or_default(retry_attempts, XSIAM_CLIENT_RETRY_ATTEMPTS)
    retry_params: Dict[str, Any] = {
        "reraise": True,
        "before_sleep": before_sleep_log(logging.getLogger(), logging.DEBUG),
        "retry": retry_if_exception_type(requests.exceptions.RequestException),
        "stop": stop_after_attempt(retry_attempts),
        "wait": wait_fixed(sleep_interval),
    }
    return Retrying(**retry_params)


def xsiam_get_installed_packs(xsiam_client: XsiamApiClient) -> List[Dict[str, Any]]:
    """Get the list of installed packs from the XSIAM tenant.
    Wrapper for XsiamApiClient.get_installed_packs() with retry logic.
    """
    return xsiam_client.installed_packs


def tenant_config_cb(
    ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]
):
    if ctx.resilient_parsing:
        return
    # Only check the params if the machine_assignment is not set.
    if param.value_is_missing(value) and not ctx.params.get("machine_assignment"):
        err_str = (
            f"{param.name} must be set either via the environment variable "
            f'"{param.envvar}" or passed explicitly when running the command'
        )
        raise typer.BadParameter(err_str)
    return value


def logs_token_cb(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]):
    if ctx.resilient_parsing:
        return
    # Only check the params if the machine_assignment is not set.
    if param.value_is_missing(value) and not ctx.params.get("machine_assignment"):
        parameter_to_check = "xsiam_token"
        other_token = ctx.params.get(parameter_to_check)
        if not other_token:
            err_str = (
                f"One of {param.name} or {parameter_to_check} must be set either via it's associated"
                " environment variable or passed explicitly when running the command"
            )
            raise typer.BadParameter(err_str)
    return value
