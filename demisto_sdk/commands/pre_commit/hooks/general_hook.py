from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class GeneralHook(Hook):
    def prepare_hook(self, **kwargs):
        self.hooks.append(self.base_hook)
