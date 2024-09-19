from copy import deepcopy
from typing import Any, Dict

from demisto_sdk.commands.pre_commit.hooks.hook import GeneratedHooks, Hook, join_files


class MypyHook(Hook):
    def prepare_hook(self) -> GeneratedHooks:
        """
        Prepares the MyPy hook for each Python version.
        Changes the hook's name, files and the "--python-version" argument according to the Python version.
        Args:
        Returns:
            None
        """
        mypy_hook_ids = []

        for python_version in self.context.python_version_to_files:
            mypy_python_version = f"mypy-py{python_version}"
            hook: Dict[str, Any] = {
                "name": mypy_python_version,
                "alias": mypy_python_version,
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(f"--python-version={python_version}")
            hook["files"] = join_files(
                self.context.python_version_to_files[python_version]
            )

            mypy_hook_ids.append(mypy_python_version)
            self.hooks.append(hook)

        return GeneratedHooks(hook_ids=mypy_hook_ids, parallel=self.parallel)
