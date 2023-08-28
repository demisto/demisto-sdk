from pathlib import Path
from typing import Sequence

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class PyclnHook(Hook):
    def prepare_hook(self, python_path: Sequence[Path], **kwargs):
        self.hook["args"] = [
            f"--skip-imports={','.join(path.name for path in python_path)},demisto,CommonServerUserPython"
        ]
