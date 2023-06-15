from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class MypyHook(Hook):
    def prepare_hook(self, python_version: str, **kwargs):
        self.hook["args"][-1] = f"--python-version={python_version}"
