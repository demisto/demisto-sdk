from packaging.version import Version

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class PEP484Hook(Hook):
    def prepare_hook(self, python_version: str, **kwargs):
        if Version(python_version) >= Version("3.10"):
            # To make this tool use PEP 604 X | None syntax instead of Optional[X].
            # This syntax is only fully supported on Python 3.10 and newer.
            self.hook["args"] = ["--use-union-or"]
