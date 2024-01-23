import sys
from copy import deepcopy
from packaging.version import Version
from pathlib import Path

from commands.content_graph.objects import Integration, Script
from commands.lint.resources.pylint_plugins.certified_partner_level_checker import cert_partner_msg
from commands.lint.resources.pylint_plugins.community_level_checker import community_msg
from commands.lint.resources.pylint_plugins.partner_level_checker import partner_msg
from commands.lint.resources.pylint_plugins.xsoar_level_checker import xsoar_msg
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files
from demisto_sdk.commands.lint.resources.pylint_plugins.base_checker import base_msg


class XsoarLinterHook(Hook):

    def prepare_hook(
        self,
    ) -> None:
        """
        Prepares the Xosar-linter hook for each Python version.
        Changes the hook's name, files and the "--target-version" argument according to the Python version.
        Args:
        """
        for integration_script_obj, files in self.context.object_to_files.items():
            xsoar_linter_env = {}
            if isinstance(integration_script_obj, Integration) and integration_script_obj.long_running:
                xsoar_linter_env["LONGRUNNING"] = "True"

            if (py_ver := integration_script_obj.python_version) and Version(py_ver).major < 3:
                xsoar_linter_env["PY2"] = "True"


            xsoar_linter_env["is_script"] = str(isinstance(integration_script_obj, Script))
            # as Xsoar checker is a pylint plugin and runs as part of pylint code, we can not pass args to it.
            # as a result we can use the env vars as a getway.
            if isinstance(integration_script_obj, Integration):
                xsoar_linter_env["commands"] = ','.join([command.name for command in integration_script_obj.commands])

            args = self.build_xsoar_linter_command(integration_script_obj.support_level)

            xsoar_linter_env_str = " ".join(f'{k}={v}' for k,v in xsoar_linter_env.items())
            hook = deepcopy(self.base_hook)

            hook.update({
                "name": f"xsoar-linter-{integration_script_obj.object_id}",
                "entry": f'env {xsoar_linter_env_str} {Path(sys.executable).parent}/{self.base_hook["entry"]}'
            })
            hook['args'].extend(args)
            hook["files"] = join_files(
                {
                    file
                    for file in files
                    if file.name == f'{integration_script_obj.path.stem}.py' and '_test' not in file.name
                }
            )
            self.hooks.append(hook)


    def build_xsoar_linter_command(self, support_level: str = "base", formatting_script: bool = False):
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
                     "xsoar_level_checker",}

        # messages from all level linters
        Msg_XSOAR_linter = {
            "base_checker": base_msg,
            "community_level_checker": community_msg,
            "partner_level_checker": partner_msg,
            "certified_partner_level_checker": cert_partner_msg,
            "xsoar_level_checker": xsoar_msg,
        }
        command = []


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