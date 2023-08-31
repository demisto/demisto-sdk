from copy import deepcopy

from demisto_sdk.commands.pre_commit.hooks.hook import Hook


class MypyHook(Hook):
    def prepare_hook(self, python_version_to_files: dict, **kwargs):
        for python_version in python_version_to_files.keys():
            hook = {"name": f"mypy-py{python_version}"} | deepcopy(self.base_hook)
            hook["args"].remove("--python-version=3.10")
            hook["args"].append(f"--python-version={python_version}")
            hook["files"] = "|".join(
                str(file) for file in python_version_to_files[python_version]
            )
            self.hooks.append(hook)
