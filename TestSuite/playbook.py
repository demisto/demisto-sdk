from pathlib import Path
from typing import Optional

import yaml
from TestSuite.file import File
from TestSuite.test_tools import suite_join_path
from TestSuite.yml import YAML


class Playbook:
    def __init__(self, tmpdir: Path, name, repo, is_test_playbook: bool = False):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.is_test_playbook = is_test_playbook

        self.path = str(tmpdir)
        self.yml = YAML(tmpdir / f'{self.name}.yml', self._repo.path)

        if not self.is_test_playbook:
            self.readme = File(tmpdir / 'README.md', self._repo.path)

        if not self.is_test_playbook:
            # build playbook
            self.create_default_playbook()
        else:
            # build test playbook
            self.create_default_test_playbook()

    def build(
            self,
            yml: Optional[dict] = None,
            readme: Optional[str] = None,
    ):
        """Writes not None objects to files.
        """
        if yml is not None:
            self.yml.write_dict(yml)
        if not self.is_test_playbook and readme is not None:
            self.readme.write(readme)

    def create_default_playbook(self):
        default_playbook_dir = 'assets/default_playbook'
        with open(suite_join_path(default_playbook_dir, 'playbook-sample.yml')) as yml:
            self.build(yml=yaml.load(yml, Loader=yaml.FullLoader))

    def create_default_test_playbook(self):
        default_test_playbook_dir = 'assets/default_playbook'
        with open(suite_join_path(default_test_playbook_dir, 'playbook-sample.yml')) as yml:
            self.build(
                yml=yaml.load(yml, Loader=yaml.FullLoader),
            )
