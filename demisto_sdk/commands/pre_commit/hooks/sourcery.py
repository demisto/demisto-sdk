import tempfile
from copy import deepcopy
from pathlib import Path

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class SourceryHook(Hook):
    def _get_temp_config_file(self, config_file_path: Path, python_version: str):
        config_file = tools.get_file_or_remote(config_file_path)
        config_file["rule_settings"]["python_version"] = python_version
        tf = tempfile.NamedTemporaryFile(delete=False)
        tools.write_yml(tf.name, config_file)
        return tf.name

    def prepare_hook(
        self, python_version_to_files: dict, config_file_path: Path, **kwargs
    ):
        hooks = self.repo["hooks"]
        base_hook = deepcopy(self.hook)
        hooks.remove(base_hook)

        for python_version in python_version_to_files.keys():
            hook = {"name": f"sourcery-py{python_version}"} | deepcopy(base_hook)
            hook["args"] += [
                f"--config={self._get_temp_config_file(config_file_path, python_version)}"
            ]
            hook["files"] = "|".join(
                str(file) for file in python_version_to_files[python_version]
            )
            hooks.append(hook)
