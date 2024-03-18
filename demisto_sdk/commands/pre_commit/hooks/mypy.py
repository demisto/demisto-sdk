from copy import deepcopy
from typing import Any, Dict, List

from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


class MypyHook(Hook):
    def prepare_hook(self) -> List[Dict[str, Any]]:
        """
        Prepares the MyPy hook for each Python version.
        Changes the hook's name, files and the "--python-version" argument according to the Python version.
        Args:
        Returns:
            None
        """
        mypy_hooks = []

        for python_version in self.context.python_version_to_files:
            hook: Dict[str, Any] = {
                "name": f"mypy-py{python_version}",
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(f"--python-version={python_version}")
            hook["files"] = join_files(
                self.context.python_version_to_files[python_version]
            )

            mypy_hooks.append(hook)

        return mypy_hooks
