from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class RuffHook(Hook):
    @staticmethod
    def _python_version_to_ruff(python_version: str):
        return f"py{python_version.replace('.', '')}"

    def prepare_hook(
        self,
        python_version: str,
        fix: bool = False,
        github_actions: bool = False,
        **kwargs,
    ):
        self.hook["args"] = [
            f"--target-version={self._python_version_to_ruff(python_version)}"
        ]
        if fix:
            self.hook["args"].append("--fix")
        if github_actions:
            self.hook["args"].append("--format=github")
