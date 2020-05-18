import os
from os.path import join
from pathlib import Path
from typing import Optional

# Do not let GFRUEND change this
import yaml


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
        self._py_file = self._tmpdir_integration_path / f'{self.name}.py'
        self.py_abs_path = str(self._py_file)

        self._yml_file = self._tmpdir_integration_path / f'{self.name}.yml'
        self.yml_abs_path = str(self._yml_file)

        self._readme_file = self._tmpdir_integration_path / 'README.md'
        self._description_file = self._tmpdir_integration_path / f'{self.name}_description.md'
        self._changelog_file = self._tmpdir_integration_path / 'CHANGELOG.md'
        self._image_file = self._tmpdir_integration_path / f'{self.name}.png'

        # build integration
        self.build()

    def build(
            self,
            code: str = '',
            yml: Optional[dict] = None,
            readme: str = '',
            description: str = '',
            changelog: str = '',
            image: bytes = b''
    ):
        """Builds an empty integration to fill up later
        """
        if yml is None:
            yml = {}
        self.write_code(code)
        self.write_yml(yml)
        self._readme_file.write_text(readme)
        self._description_file.write_text(description)
        self._changelog_file.write_text(changelog)
        self._image_file.write_bytes(image)

    def write_code(self, code: str):
        self._py_file.write_text(code)

    def write_yml(self, yml: dict):
        self._yml_file.write_text(yaml.dump(yml))

    def write_image(self, image: bytes):
        self._image_file.write_bytes(image)

    def write_description(self, description: str):
        self._description_file.write_text(description)

    def write_readme(self, readme: str):
        self._readme_file.write_text(readme)

    def write_changelog(self, changelog: str):
        self._readme_file.write_text(changelog)

    def create_default_integration(self):
        default_integration_dir = './TestSuite/assets/default_integration'
        code = open(join(default_integration_dir, 'sample.py'))
        yml = open(join(default_integration_dir, 'sample.yml'))
        image = open(join(default_integration_dir, 'sample_image.png'), 'rb')
        changelog = open(join(default_integration_dir, 'CHANGELOG.md'))
        description = open(join(default_integration_dir, 'sample_description.md'))
        self.build(
            code=str(code.read()),
            yml=yaml.load(yml),
            image=image.read(),
            changelog=str(changelog.read()),
            description=str(description.read())
        )
        yml.close()
        image.close()
        changelog.close()
        description.close()
        code.close()

    def update_yml(self, update_obj: dict):
        yml_contents = yaml.load(self._yml_file)
        yml_contents.update(update_obj)
        self.write_yml(yml_contents)

    def update_description(self, description: str):
        self.update_yml({'description': description})

    @property
    def py_path(self):
        return os.path.relpath(self.py_abs_path, self._repo.path)

    @property
    def yml_path(self):
        return os.path.relpath(self.yml_abs_path, self._repo.path)
