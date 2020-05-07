import json
from pathlib import Path

from TestSuite.secrets import Secrets


class GlobalSecrets(Secrets):
    def __init__(self, tmpdir: Path):
        global_secrets_path = './Tests/secrets_white_list.json'
        super().__init__(tmpdir, global_secrets_path)

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
        self._secrets_path.write_text(json.dumps(secrets_content))
