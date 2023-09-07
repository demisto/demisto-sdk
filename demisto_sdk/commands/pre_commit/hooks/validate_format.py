from pathlib import Path
from typing import Iterable, Optional

from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files


class ValidateFormatHook(Hook):
    def prepare_hook(self, files_to_run: Optional[Iterable[Path]], **kwargs):
        """
        Prepares the Validate or the Format hook.
        The default value is -g flag. In case of an input, we need to change it to -i, and add the input files.
        Args:
            input_files (Optional[Iterable[Path]]): The input files to validate. Defaults to None.
        """
        if self.input_mode:
            self.base_hook["args"].append("-i")
            self.base_hook["args"].append(join_files(files_to_run, ","))
        elif self.all_files:
            self.base_hook["args"].append("-a")
        else:
            self.base_hook["args"].append("-g")

        self.hooks.append(self.base_hook)
