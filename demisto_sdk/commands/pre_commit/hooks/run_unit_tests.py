from demisto_sdk.commands.pre_commit.hooks.hook import GeneratedHooks, Hook


class RunUnitTestHook(Hook):
    def prepare_hook(self, **kwargs) -> GeneratedHooks: ...
