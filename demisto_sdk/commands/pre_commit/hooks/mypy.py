from copy import deepcopy

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class MypyHook(Hook):
    def prepare_hook(self, python_version_to_files: dict, **kwargs):
        hooks = self.repo["hooks"]
        base_hook = deepcopy(self.hook)
        hooks.remove(base_hook)

        for python_version in python_version_to_files.keys():
            hook = {"name": f"mypy-py{python_version}"} | deepcopy(base_hook)
            hook["args"][-1] = f"--python-version={python_version}"
            hook["files"] = "|".join(
                str(file) for file in python_version_to_files[python_version]
            )
            hooks.append(hook)
