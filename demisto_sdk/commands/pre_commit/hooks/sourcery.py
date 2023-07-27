import tempfile
from pathlib import Path

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class SourceryHook(Hook):
    def prepare_hook(self, python_version: str, config_file_path: Path, **kwargs):
        config_file = tools.get_file_or_remote(config_file_path)
        config_file["rule_settings"]["python_version"] = python_version
        # tmp_file_path = config_file_path.with_name(".sourcery_tmp.yaml")
        tf = tempfile.NamedTemporaryFile(delete=False)
        tools.write_yml(tf.name, config_file)
        self.hook["args"] += [f"--config={tf.name}"]
