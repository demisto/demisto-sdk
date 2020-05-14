from pathlib import Path


class Secrets:
    def __init__(self, temp_path: Path):
        file_name = '.secrets-ignore'
        self._secrets_path = temp_path / file_name
        self.path = str(self._secrets_path)
        self.write_secrets([])

    def write_secrets(self, secrets: list):
        self._secrets_path.write_text('\n'.join(secrets))
