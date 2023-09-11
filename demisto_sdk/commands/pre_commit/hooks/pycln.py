from pathlib import Path
from typing import Sequence

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class PyclnHook(Hook):
    def prepare_hook(self, python_path: Sequence[Path], **kwargs):
        """
        Prepares the Pycln hook.
        Adds the "--skip-imports" argument with all the imports that should be skipped and not removed.
        Args:
            python_path (Sequence[Path]): A sequence of paths to Python files.
        Returns:
            None
        """
        self.base_hook["args"] = [
            f"--skip-imports={','.join(path.name for path in python_path)},demisto,CommonServerUserPython"
        ]

        self.hooks.append(self.base_hook)
