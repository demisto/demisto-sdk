from pathlib import Path
from typing import Iterable, Optional

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class ValidateFormatHook(Hook):
    def prepare_hook(self, input_files: Optional[Iterable[Path]], **kwargs):
        if input_files:
            # The default value is -g flag. In case of an input, we need to change it to -i, and add the input files
            self.hook["args"].remove("-g")
            self.hook["args"].append("-i")
            self.hook["args"].append(",".join(str(file) for file in input_files))
