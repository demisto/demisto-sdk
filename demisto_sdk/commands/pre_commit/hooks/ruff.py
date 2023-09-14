from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Set

from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


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
        python_version_to_files: Dict[str, Set[Path]],
        github_actions: bool = False,
        **kwargs,
    ) -> None:
        """
        Prepares the Ruff hook for each Python version.
        Changes the hook's name, files and the "--target-version" argument according to the Python version.
        Args:
            python_version_to_files (Dict[str, Set[Path]]): dictionary mapping python version to files
            github_actions (bool, optional): Whether to use github actions format. Defaults to False.
        """
        for python_version in python_version_to_files:
            hook: Dict[str, Any] = {
                "name": f"ruff-py{python_version}",
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"] = [
                f"--target-version={self._python_version_to_ruff(python_version)}",
            ]
            if self.all_files:
                hook["args"].append("--config=nightly_ruff.toml")
            else:
                hook["args"].append("--fix")
            if github_actions:
                hook["args"].append("--format=github")
            hook["files"] = join_files(python_version_to_files[python_version])

            self.hooks.append(hook)
