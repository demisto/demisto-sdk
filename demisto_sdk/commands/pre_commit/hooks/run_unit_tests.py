from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class RunUnitTestHook(Hook):
    def prepare_hook(self, **kwargs):
        ...
