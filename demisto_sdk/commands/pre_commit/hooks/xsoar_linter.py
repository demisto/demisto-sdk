import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any

from commands.content_graph.common import ContentType
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
        for support_level, files_with_object in self.context.support_level_to_files_with_objects.items():
            args = self.build_xsoar_linter_command(support_level)
            hook: Dict[str, Any] = {
                "name": f"xsoar-linter-{support_level}",
                "args": args,
                "entry": f'{Path(sys.executable).parent}/{self.base_hook["entry"]}'
            }
            hook["files"] = join_files(
                {
                    file
                    for file, obj in files_with_object
                    if file.suffix == ".py" and obj.content_type == ContentType.INTEGRATION
                }
            )
            hook.update(deepcopy(self.base_hook))
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
        # Disable all errors
        command.append("-E")
        command.append("--disable=all")
        # Message format
        command.append("--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'")
        # Enable only Demisto Plugins errors.
        command.append(f"--enable={message_enable}")
        # Load plugins
        if checker_path:
            command.append(f"--load-plugins={checker_path}")
        return command