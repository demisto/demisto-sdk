from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Set

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
        language_to_files: Dict[str, Set[Path]],
        github_actions: bool = False,
        **kwargs,
    ) -> None:
        """
        Prepares the Ruff hook for each Python version.
        Changes the hook's name, files and the "--target-version" argument according to the Python version.
        Args:
            language_to_files (Dict[str, Set[Path]]): dictionary mapping python version to files
            github_actions (bool, optional): Whether to use github actions format. Defaults to False.
        """
        for version in language_to_files:
            if version in ["powershell", "javascript"]:
                continue
            hook: Dict[str, Any] = {
                "name": f"ruff-py{version}",
            }
            hook.update(deepcopy(self.base_hook))
            target_version = (
                f"--target-version={self._python_version_to_ruff(version)}"
            )
            safe_update_hook_args(hook, target_version)
            if github_actions:
                hook["args"].append("--format=github")
            hook["files"] = join_files(language_to_files[version])

            self.hooks.append(hook)
