import sys
from pathlib import Path

from demisto_sdk.commands.pre_commit.hooks.hook import (
    GeneratedHooks,
    Hook,
)


class SystemHook(Hook):
    def prepare_hook(self) -> GeneratedHooks:
        """
        Prepares the Validate or the Format hook.
        In case of nightly mode and all files, runs validate/format with the --all flag, (nightly mode is not supported on specific files).
        In case of an input or all files without nightly, runs validate/format on the given files.
        Otherwise runs validate/format with the -g flag.
        Args:
            files_to_run (Optional[Iterable[Path]]): The input files to validate. Defaults to None.
        """
        if "entry" in self.base_hook:
            entry = self.base_hook["entry"]
            bin_path = Path(sys.executable).parent
            self.base_hook["entry"] = (
                f"{bin_path}/{entry}" if str(bin_path) not in entry else entry
            )
        self.hooks.insert(self.hook_index, self.base_hook)
        return GeneratedHooks(hook_ids=[self.base_hook["id"]], parallel=self.parallel)
