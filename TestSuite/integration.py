from pathlib import Path


class Integration:
    def __init__(self, tmpdir: Path, name):
        self.name = name
        self._integrations_tmpdir = tmpdir
        self._tmpdir_integration_path = self._integrations_tmpdir / f'{self.name}'
        if not self._integrations_tmpdir.exists():
            self._integrations_tmpdir.mkdir()
        if not self._tmpdir_integration_path.exists():
            self._tmpdir_integration_path.mkdir()
        self.path = str(self._tmpdir_integration_path)
        self._py_file = self._tmpdir_integration_path / f'{self.name}.py'
        self.py_path = str(self._py_file)
        self._yml_file = self._tmpdir_integration_path / f'{self.name}.yml'
        self._readme_file = self._tmpdir_integration_path / 'README.md'
        self._description_file = self._tmpdir_integration_path / f'{self.name}_description.md'
        self._changelog_file = self._tmpdir_integration_path / 'CHANGELOG.md'
        self._image_file = self._tmpdir_integration_path / f'{self.name}.png'
        self.build()

    def build(
            self,
            code: str = '',
            yml: str = '',
            readme: str = '',
            description: str = '',
            changelog: str = '',
            image: bytes = b''
    ):
        """Builds an empty integration to fill up later
        """
        self._py_file.write_text(code)
        self._yml_file.write_text(yml)
        self._readme_file.write_text(readme)
        self._description_file.write_text(description)
        self._changelog_file.write_text(changelog)
        self._image_file.write_bytes(image)

    def write_code(self, code: str):
        self._py_file.write_text(code)
