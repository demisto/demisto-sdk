import json
from pathlib import Path


class GlobalSecrets:
    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        file_name = 'secrets_white_list.json'
        self._secrets_path = tmpdir / file_name
        self.path = str(self._secrets_path)

    def write_secrets(self, urls=None, ips=None, files=None, generic_strings=None):
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
        self._secrets_path.write_text(json.dumps(secrets_content), None)
