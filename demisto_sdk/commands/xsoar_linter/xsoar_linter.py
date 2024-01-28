import multiprocessing
import os
import re
import subprocess
import sys
from packaging.version import Version
from pathlib import Path
from typing import Optional, List

import typer as typer

from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.content_constant_paths import PYTHONPATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.lint.resources.pylint_plugins.base_checker import base_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.certified_partner_level_checker import cert_partner_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.community_level_checker import community_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.partner_level_checker import partner_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.xsoar_level_checker import xsoar_msg
from demisto_sdk.commands.content_graph.objects import Integration, Script
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript

xsoar_linter_app = typer.Typer(name="Pre-Commit")
ENV = os.environ


def build_xsoar_linter_command(support_level: str = "base", formatting_script: bool = False):
    if not support_level:
        support_level = "base"
    # linters by support level
    support_levels = {
        "base": "base_checker",
        "community": "base_checker,community_level_checker",
        "partner": "base_checker,community_level_checker,partner_level_checker",
        "certified partner": "base_checker,community_level_checker,partner_level_checker,"
                             "certified_partner_level_checker",
        "xsoar": "base_checker,community_level_checker,partner_level_checker,certified_partner_level_checker,"
                 "xsoar_level_checker", }
    # messages from all level linters
    Msg_XSOAR_linter = {
        "base_checker": base_msg,
        "community_level_checker": community_msg,
        "partner_level_checker": partner_msg,
        "certified_partner_level_checker": cert_partner_msg,
        "xsoar_level_checker": xsoar_msg,
    }

    command = [f'{Path(sys.executable).parent}/pylint']
    command.append(f"-E")
    command.append(f"--disable=all")
    command.append(
        f"--fail-under=-100")  # With this flag, the linter will fail only if the score is less than -100, which isn't possible with warnings.
    command.append(f"--fail-on=E")  # we want the pylint to fail on Errors and fatals

    checker_path = ""
    message_enable = ""
    if support_levels.get(support_level):
        checkers = support_levels.get(support_level)
        support = checkers.split(",") if checkers else []
        for checker in support:
            checker_path += f"{checker},"
            checker_msgs_list = Msg_XSOAR_linter.get(checker, {}).keys()
            if formatting_script and "W9008" in checker_msgs_list:
                checker_msgs_list = [msg for msg in checker_msgs_list if msg != "W9008"]
            for msg in checker_msgs_list:
                message_enable += f"{msg},"
    # Message format
    command.append("--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'")
    # Enable only Demisto Plugins errors.
    command.append(f"--enable={message_enable}")
    # Load plugins
    if checker_path:
        command.append(f"--load-plugins={checker_path}")

    return command


def process_file(file_path):
    errors = []
    env = ENV.copy()
    integration_script = BaseContent.from_path(file_path)
    if not isinstance(integration_script, IntegrationScript):
        return 0
    file = integration_script.path.parent / f'{integration_script.path.stem}.py'
    if not file.exists():
        return 0

    xsoar_linter_env = {}
    if isinstance(integration_script, Integration) and integration_script.long_running:
        xsoar_linter_env["LONGRUNNING"] = "True"

    if (py_ver := integration_script.python_version) and Version(py_ver).major < 3:
        xsoar_linter_env["PY2"] = "True"

    xsoar_linter_env["is_script"] = str(isinstance(integration_script, Script))
    # as Xsoar checker is a pylint plugin and runs as part of pylint code, we can not pass args to it.
    # as a result we can use the env vars as a getway.
    if isinstance(integration_script, Integration):
        xsoar_linter_env["commands"] = ','.join([command.name for command in integration_script.commands])
    command = build_xsoar_linter_command(integration_script.support_level)
    command.append(str(file))

    env.update(xsoar_linter_env)
    env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
    try:
        process = subprocess.run(command, capture_output=True, env=env, timeout=60)
        return_code = process.returncode
        log_data = process.stdout
        log_str = log_data.decode('utf-8')
        pattern = re.compile(r'^/[^:\n]+:\d+:\d+: E\d+ .*$', re.MULTILINE)
        errors += pattern.findall(log_str)
        errors_str = '\n'.join(errors) if errors else ''
    except subprocess.TimeoutExpired:
        logger.error("Timeout")
        return_code = 1
    return return_code, errors_str

def xsoar_linter_manager(
    file_paths: Optional[List[Path]]):

    if not file_paths:
        return 0

    with multiprocessing.Pool(processes=cpu_count()) as pool:
        # Map the file_paths to the process_file function using the pool
        results = pool.map(process_file, file_paths)

    return_codes, errors = zip(*results)
    if errors:
        errors_str = '\n'.join(errors)
        logger.error(f'Found the following errors: \n{errors_str}')
    return int(any(return_codes))