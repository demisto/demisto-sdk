import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.pre_commit.hooks.hook import GeneratedHooks, Hook, join_files


class SourceryHook(Hook):
    def _get_temp_config_file(self, config_file_path: Path, python_version):
        """
        Gets a temporary configuration file with the specified Python version.
        Args:
            config_file_path (Path): The path to the configuration file.
            python_version (str): The Python version to set in the configuration file.
        Returns:
            str: The path to the temporary configuration file.
        """
        config_file = tools.get_file_or_remote(config_file_path)
        config_file["rule_settings"]["python_version"] = python_version
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
        tools.write_dict(tf.name, data=config_file)
        return tf.name

    def prepare_hook(self) -> GeneratedHooks:
        """
        Prepares the Sourcery hook for each Python version.
        Changes the hook's name, files and the "--config" argument according to the Python version.
        Args:
        Returns:
            None
        """
        config_file = CONTENT_PATH / self._get_property("config_file", ".sourcery.yml")
        if not config_file.exists():
            return []
        self.base_hook.pop("config_file", None)

        sourcery_hook_ids = []
        for python_version in self.context.python_version_to_files:
            sourcery_python_version = f"sourcery-py{python_version}"
            hook: Dict[str, Any] = {
                "name": sourcery_python_version,
                "alias": sourcery_python_version,
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(
                f"--config={self._get_temp_config_file(config_file, python_version)}"
            )
            hook["files"] = join_files(
                self.context.python_version_to_files[python_version]
            )
            sourcery_hook_ids.append(sourcery_python_version)
            self.hooks.append(hook)

        return GeneratedHooks(hook_ids=sourcery_hook_ids, parallel=self.parallel)
