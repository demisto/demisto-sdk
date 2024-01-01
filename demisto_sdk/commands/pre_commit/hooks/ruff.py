import os
from copy import deepcopy
from typing import Any, Dict

from demisto_sdk.commands.pre_commit.hooks.hook import (
    Hook,
    join_files,
    safe_update_hook_args,
)


class RuffHook(Hook):
    @staticmethod
    def _python_version_to_ruff(python_version: str):
        """
        Converts a Python version of the form "x.y" to a Ruff version of the form "pyxy".
        Args:
            python_version (str): The Python version string.
        Returns:
            str: The Ruff version string.
        """
        return f"py{python_version.replace('.', '')}"

    def prepare_hook(
        self,
    ) -> None:
        """
        Prepares the Ruff hook for each Python version.
        Changes the hook's name, files and the "--target-version" argument according to the Python version.
        Args:
        """
        for python_version in self.context.python_version_to_files:
            hook: Dict[str, Any] = {
                "name": f"ruff-py{python_version}",
            }
            hook.update(deepcopy(self.base_hook))
            target_version = (
                f"--target-version={self._python_version_to_ruff(python_version)}"
            )
            safe_update_hook_args(hook, target_version)
            if os.getenv("GITHUB_ACTIONS", False):
                hook["args"].append("--format=github")
            hook["files"] = join_files(
                {
                    file
                    for file in self.context.python_version_to_files[python_version]
                    if file.suffix == ".py"
                }
            )

            self.hooks.append(hook)
