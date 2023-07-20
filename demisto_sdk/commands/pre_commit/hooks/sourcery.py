from demisto_sdk.commands.common import tools
from demisto_sdk.commands.pre_commit.hooks.hook import Hook
from pathlib import Path


class SourceryHook(Hook):
    def prepare_hook(self, python_version: str, config_file_path: Path, **kwargs):
        config_file = tools.get_file_or_remote(config_file_path)
        config_file["rule_settings"]["python_version"] = python_version
        tmp_file_path = config_file_path.with_name("sourcery_tmp.yml")
        self.hook["args"] = [
            f"--config={tmp_file_path}",
            "--no-summary",
            "--fix",
            "--diff=git diff HEAD",
        ]
        tools.write_yml(str(tmp_file_path), config_file)
