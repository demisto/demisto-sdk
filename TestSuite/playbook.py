from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.file import File
from TestSuite.test_suite_base import TestSuiteBase
from TestSuite.test_tools import suite_join_path
from TestSuite.yml import YAML
from demisto_sdk.commands.common.tools import set_value

yaml = YAML_Handler()


class Playbook(YAML):

    default_assets_dir = "assets"

    def __init__(self, tmpdir: Path, name, repo, is_test_playbook: bool = False):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.is_test_playbook = is_test_playbook

        self.path = str(tmpdir)

        super().__init__(tmp_path=tmpdir / f"{self.name}.yml", repo_path=str(repo.path))
        if not self.is_test_playbook:
            self.readme = File(tmpdir / f"{self.name}_README.md", self._repo.path)

        if not self.is_test_playbook:
            # build playbook
            self.create_default_playbook()
        else:
            # build test playbook
            self.create_default_test_playbook()
    
    @property
    def yml(self):
        # for backward compatible
        return self
    
    def build(
        self,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
    ):
        """Writes not None objects to files."""
        if yml is not None:
            self.write_dict(yml)
        if not self.is_test_playbook and readme is not None:
            self.readme.write(readme)

    def create_default_playbook(self, name: str = "sample playbook"):
        """Creates a new playbook with basic data.

        Args:
            name: The name and ID of the new playbook, default is "sample playbook".

        """
        default_playbook_dir = "assets/default_playbook"
        with open(
            suite_join_path(default_playbook_dir, "playbook-sample.yml")
        ) as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = yml["name"] = name
            self.build(yml=yml)

    def create_default_test_playbook(self, name: str = "SamplePlaybookTest"):
        with open(
            suite_join_path(
                self.default_assets_dir, "default_playbook/playbook-sample.yml"
            )
        ) as yml_file:
            yml = yaml.load(yml_file)
            yml["id"] = yml["name"] = name
            self.build(yml=yml)

    def add_default_task(self, task_script_name: str = None):
        task = None
        task_filename = "default_playbook/tasks/task-sample.yml"
        with open(
            suite_join_path(self.default_assets_dir, task_filename)
        ) as task_yml_file:
            task = yaml.load(task_yml_file)
        if not task:
            print(  # noqa: T201
                "Cannot read task from "
                + task_filename
                + ", not adding task to playbook"
            )
            return

        if task_script_name:
            set_value(task, 'task.scriptName', task_script_name)
        original_yml = self.read_dict()
        tasks = original_yml["tasks"]
        last_task = tasks[next(reversed(tasks))]
        last_task["nexttasks"] = {"#none#": [task["id"]]}
        tasks.insert(len(tasks), task["id"], task)
        self.build(yml=original_yml)
