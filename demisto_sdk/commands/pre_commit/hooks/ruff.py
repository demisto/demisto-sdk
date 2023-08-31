from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Set

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class RuffHook(Hook):
    @staticmethod
    def _python_version_to_ruff(python_version: str):
        return f"py{python_version.replace('.', '')}"

    def prepare_hook(
        self,
        python_version_to_files: Dict[str, Set[Path]],
        github_actions: bool = False,
        **kwargs,
    ) -> None:
        for python_version in python_version_to_files.keys():
            hook: Dict[str, Any] = {
                "name": f"ruff-py{python_version}",
                **deepcopy(self.base_hook),
            }
            hook["args"] = [
                f"--target-version={self._python_version_to_ruff(python_version)}",
                "--fix",
            ]
            if github_actions:
                hook["args"].append("--format=github")
            hook["files"] = self._join_files(python_version_to_files[python_version])
            self.hooks.append(hook)
