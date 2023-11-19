from copy import deepcopy
from typing import Any, Dict

from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


class MypyHook(Hook):
    def prepare_hook(self, language_to_files: dict, **kwargs):
        """
        Prepares the MyPy hook for each Python version.
        Changes the hook's name, files and the "--python-version" argument according to the Python version.
        Args:
            language_to_files (dict): A dictionary mapping Python versions to files.
        Returns:
            None
        """
        for version in language_to_files:
            if version in ["powershell", "javascript"]:
                continue
            hook: Dict[str, Any] = {
                "name": f"mypy-py{version}",
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(f"--python-version={version}")
            hook["files"] = join_files(language_to_files[version])

            self.hooks.append(hook)
