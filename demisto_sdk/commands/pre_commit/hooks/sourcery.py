import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


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

    def prepare_hook(
        self, python_version_to_files: dict, config_file_path: Path, **kwargs
    ):
        """
        Prepares the Sourcery hook for each Python version.
        Changes the hook's name, files and the "--config" argument according to the Python version.
        Args:
            python_version_to_files (dict): A dictionary mapping Python versions to files.
            config_file_path (Path): The path to the configuration file.
        Returns:
            None
        """
        for python_version in python_version_to_files:
            hook: Dict[str, Any] = {
                "name": f"sourcery-py{python_version}",
            }
            hook.update(deepcopy(self.base_hook))
            hook["args"].append(
                f"--config={self._get_temp_config_file(config_file_path, python_version)}"
            )
            hook["files"] = join_files(python_version_to_files[python_version])

            self.hooks.append(hook)
