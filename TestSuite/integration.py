from pathlib import Path
from typing import Optional

import yaml
from deprecated import deprecated
from TestSuite.file import File
from TestSuite.test_tools import suite_join_path
from TestSuite.yml import YAML


class Integration:
    def __init__(self, tmpdir: Path, name, repo):
        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path

        # Create paths
        self._tmpdir_integration_path = tmpdir / f'{self.name}'
        self._tmpdir_integration_path.mkdir()

        self.path = str(self._tmpdir_integration_path)
        self.code = File(self._tmpdir_integration_path / f'{self.name}.py', self._repo.path)
        self.yml = YAML(self._tmpdir_integration_path / f'{self.name}.yml', self._repo.path)
        self.readme = File(self._tmpdir_integration_path / 'README.md', self._repo.path)
        self.description = File(self._tmpdir_integration_path / f'{self.name}_description.md', self._repo.path)
        self.changelog = File(self._tmpdir_integration_path / 'CHANGELOG.md', self._repo.path)
        self.image = File(self._tmpdir_integration_path / f'{self.name}.png', self._repo.path)

        # build integration
        self.create_default_integration()

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

    def create_default_integration(self):
        default_integration_dir = 'assets/default_integration'
        code = open(suite_join_path(default_integration_dir, 'sample.py'))
        yml = open(suite_join_path(default_integration_dir, 'sample.yml'))
        image = open(suite_join_path(default_integration_dir, 'sample_image.png'), 'rb')
        changelog = open(suite_join_path(default_integration_dir, 'CHANGELOG.md'))
        description = open(suite_join_path(default_integration_dir, 'sample_description.md'))
        self.build(
            code=str(code.read()),
            yml=yaml.load(yml, Loader=yaml.FullLoader),
            image=image.read(),
            changelog=str(changelog.read()),
            description=str(description.read())
        )
        yml.close()
        image.close()
        changelog.close()
        description.close()
        code.close()

    # Deprecated methods

    @deprecated(reason="use integration.code.write instead")
    def write_code(self, code: str):
        self.code.write(code)

    @deprecated(reason="use integration.code.read instead")
    def read_code(self):
        return self.code.read()

    @deprecated(reason="use integration.yml.write_dict instead")
    def write_yml(self, yml: dict):
        self.yml.write_dict(yml)

    @deprecated(reason="use integration.image.write_bytes instead")
    def write_image(self, image: bytes):
        self.image.write_bytes(image)

    @deprecated(reason="use integration.description.write instead")
    def write_description(self, description: str):
        self.description.write(description)

    @deprecated(reason="use integration.readme.write instead")
    def write_readme(self, readme: str):
        self.readme.write(readme)

    @deprecated(reason="use integration.readme.write instead")
    def write_changelog(self, changelog: str):
        self.readme.write(changelog)

    @deprecated(reason="use integration.yml.update instead")
    def update_yml(self, update_obj: dict):
        yml_contents = yaml.load(self.yml.read())
        yml_contents.update(update_obj)
        self.yml.write(yml_contents)

    @deprecated(reason="use integration.yml.update_description instead")
    def update_description(self, description: str):
        self.yml.update_description(description)

    @property
    @deprecated(reason="use integration.code.rel_path instead")
    def py_path(self):
        return self.code.rel_path

    @property
    @deprecated(reason="use integration.yml.rel_path instead")
    def yml_path(self):
        return self.yml.rel_path
