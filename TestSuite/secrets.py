import json
from pathlib import Path


class Secrets:
    def __init__(self, tmpdir: Path, secrets_path: str = '.secrets-ignore'):
        self.tmpdir = tmpdir
        secrets_paths = secrets_path.split('/')
        file_name = secrets_paths.pop(-1)
        temp_path = tmpdir
        for path in secrets_paths:
            temp_path = tmpdir / path
            if not temp_path.exists():
                temp_path.mkdir()
        self._secrets_path = temp_path / file_name
        self.path = str(self._secrets_path)

    def write_secrets(self, secrets: list):
        self._secrets_path.write_text('\n'.join(secrets))

    def write_global_secrets(self, urls=None, ips=None, files=None, generic_strings=None):
        if files is None:
            files = []
        if urls is None:
            urls = []
        if ips is None:
            ips = []
        if generic_strings is None:
            generic_strings = []
        secrets_content = dict(
            files=files,
            iocs=dict(
                ips=ips,
                urls=urls
            ),
            generic_strings=generic_strings
        )
        self._secrets_path.write_text(json.dumps(secrets_content))
