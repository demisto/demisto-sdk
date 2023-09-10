from copy import deepcopy
from typing import Any, Dict

from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


class MypyHook(Hook):
    def prepare_hook(self, python_version_to_files: dict, **kwargs):
        """
        Prepares the MyPy hook for each Python version.
        Changes the hook's name, files and the "--python-version" argument according to the Python version.
        Args:
            python_version_to_files (dict): A dictionary mapping Python versions to files.
        Returns:
            None
        """
        for python_version in python_version_to_files:
            hook: Dict[str, Any] = {
                "name": f"mypy-py{python_version}",
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(f"--python-version={python_version}")
            hook["files"] = join_files(python_version_to_files[python_version])

            self.hooks.append(hook)
