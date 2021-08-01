import os
import shutil
from pathlib import Path
from typing import List, Optional

import yaml

from demisto_sdk.commands.unify.yml_unifier import YmlUnifier
from TestSuite.file import File
from TestSuite.test_tools import suite_join_path
from TestSuite.yml import YAML


class Integration:
    def __init__(self, tmpdir: Path, name, repo, create_unified: Optional[bool] = False):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path

        # Create paths
        self._tmpdir_integration_path = tmpdir / f'{self.name}'
        self._tmpdir_integration_path.mkdir()

        # if creating a unified yaml
        self.create_unified = create_unified

        self.path = str(self._tmpdir_integration_path)
        self.code = File(self._tmpdir_integration_path / f'{self.name}.py', self._repo.path)
        self.yml = YAML(self._tmpdir_integration_path / f'{self.name}.yml', self._repo.path)
        self.readme = File(self._tmpdir_integration_path / 'README.md', self._repo.path)
        self.description = File(self._tmpdir_integration_path / f'{self.name}_description.md', self._repo.path)
        self.changelog = File(self._tmpdir_integration_path / 'CHANGELOG.md', self._repo.path)
        self.image = File(self._tmpdir_integration_path / f'{self.name}_image.png', self._repo.path)

    def build(
            self,
            code: Optional[str] = None,
            yml: Optional[dict] = None,
            readme: Optional[str] = None,
            description: Optional[str] = None,
            changelog: Optional[str] = None,
            image: Optional[bytes] = None
    ):
        """Writes not None objects to files.
        """
        if code is not None:
            self.code.write(code)
        if yml is not None:
            self.yml.write_dict(yml)
        if readme is not None:
            self.readme.write(readme)
        if description is not None:
            self.description.write(description)
        if changelog is not None:
            self.changelog.write(changelog)
        if image is not None:
            self.image.write_bytes(image)

    def create_default_integration(self, name: str = 'Sample', commands: List[str] = None):
        """Creates a new integration with basic data

        Args:
            name: The name and ID of the new integration, default is "Sample".
            commands: List of additional commands to add to the integration.

        """
        default_integration_dir = 'assets/default_integration'

        with open(suite_join_path(default_integration_dir, 'sample.py')) as code_file:
            code = str(code_file.read())
        with open(suite_join_path(default_integration_dir, 'sample.yml')) as yml_file:
            yml = yaml.safe_load(yml_file)
            yml['name'] = yml['commonfields']['id'] = name
            if commands:
                for command in commands:
                    yml['script']['commands'].append({'name': command})
        with open(suite_join_path(default_integration_dir, 'sample_image.png'), 'rb') as image_file:
            image = image_file.read()
        with open(suite_join_path(default_integration_dir, 'CHANGELOG.md')) as changelog_file:
            changelog = str(changelog_file.read())
        with open(suite_join_path(default_integration_dir, 'sample_description.md')) as description_file:
            description = str(description_file.read())

        self.build(
            code=code,
            yml=yml,
            image=image,
            changelog=changelog,
            description=description
        )

        if self.create_unified:
            unifier = YmlUnifier(input=self.path, output=os.path.dirname(self._tmpdir_integration_path))
            unifier.merge_script_package_to_yml()
            shutil.rmtree(self._tmpdir_integration_path)
