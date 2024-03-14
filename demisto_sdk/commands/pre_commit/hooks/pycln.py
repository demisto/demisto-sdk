from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.pre_commit.hooks.hook import (
    Hook,
    safe_update_hook_args,
)


class PyclnHook(Hook):
    def prepare_hook(self):
        """
        Prepares the Pycln hook.
        Adds the "--skip-imports" argument with all the imports that should be skipped and not removed.
        Args:
            python_path (Sequence[Path]): A sequence of paths to Python files.
        Returns:
            None
        """
        paths_to_skip = tuple(
            path.name
            for path in PYTHONPATH
            if path.absolute() != CONTENT_PATH.absolute()
        )
        builtins_to_skip = ("demisto", "CommonServerUserPython")

        skip_imports = f"--skip-imports={','.join(paths_to_skip + builtins_to_skip)}"
        safe_update_hook_args(self.base_hook, skip_imports)

        self.hooks.append(self.base_hook)
