from pathlib import Path
from typing import Iterable, Optional

from demisto_sdk.commands.common.constants import PreCommitModes
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


class ValidateFormatHook(Hook):
    def prepare_hook(self, files_to_run: Optional[Iterable[Path]], **kwargs):
        """
        Prepares the Validate or the Format hook.
        In case of nightly mode and all files, runs validate/format with the --all flag, (nightly mode is not supported on specific files).
        In case of an input or all files without nightly, runs validate/format on the given files.
        Otherwise runs validate/format with the -g flag.
        Args:
            input_files (Optional[Iterable[Path]]): The input files to validate. Defaults to None.
        """
        if self.mode == PreCommitModes.NIGHTLY and self.all_files:
            self.base_hook["args"].append("-a")
        elif self.input_mode or self.all_files:
            self.base_hook["args"].append("-i")
            self.base_hook["args"].append(join_files(files_to_run, ","))
        else:
            self.base_hook["args"].append("-g")

        self.hooks.insert(self.hook_index, self.base_hook)
