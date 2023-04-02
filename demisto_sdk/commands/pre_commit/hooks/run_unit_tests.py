from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class RunUnitTestHook(Hook):
    def prepare_hook(self, native_images: bool = False, **kwargs):
        if native_images:
            self.hook["args"] = ["--native-images"]
