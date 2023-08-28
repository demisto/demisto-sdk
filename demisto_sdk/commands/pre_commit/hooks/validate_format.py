from pathlib import Path
from typing import Iterable, Optional

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class ValidateFormatHook(Hook):
    def prepare_hook(self, input_files: Optional[Iterable[Path]], **kwargs):
        if input_files:
            base_hooks = [hook for hook in self.repo["hooks"] if hook["id"]]
            hooks = self.repo["hooks"] = []
            for hook in base_hooks:
                if hook["id"] in ("validate", "format"):
                    # The default value is -g flag. In case of an input, we need to change it to -i, and add the input files
                    hook["args"].remove("-g")
                    hook["args"].append("-i")
                    hook["args"].append(",".join(str(file) for file in input_files))
                hooks.append(hook)
