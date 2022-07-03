from __future__ import annotations

from typing import TYPE_CHECKING

from demisto_sdk.commands.common.constants import SAMPLES_DIR
from TestSuite.json_based import JSONBased

if TYPE_CHECKING:
    from TestSuite.repo import Repo

from pathlib import Path

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.file import File
from TestSuite.yml import YAML

yaml = YAML_Handler()


class Rule:
    def __init__(
        self,
        tmpdir: Path,
        name: str,
        repo: Repo,
    ):
        self.name = name
        self._repo = repo
        self.repo_path = repo.path

        self._tmpdir_rule_path = tmpdir / f'{self.name}'
        self._tmpdir_rule_path.mkdir()

        self.path = str(self._tmpdir_rule_path)
        self.yml = YAML(self._tmpdir_rule_path / f'{self.name}.yml', self._repo.path)
        self.rules = File(self._tmpdir_rule_path / f'{self.name}.xif', self._repo.path)
        self.samples: list[JSONBased] = []
        self.samples_dir_path = tmpdir / SAMPLES_DIR
        self.schema = File(self._tmpdir_rule_path / f'{self.name}.json', self._repo.path)

    def build(
            self,
            yml: dict,
            rules: str | None = None,
            samples: list[dict] | None = None,
            schema: dict | None = None,
    ):
        self.yml.write_dict(yml)
        if rules:
            self.rules.write(rules)
        if schema:
            schema_file = JSONBased(
                dir_path=self._tmpdir_rule_path,
                name=f'{self.name}.json',
                prefix=''
            )
            schema_file.write_json(schema)

        if samples:
            self.samples_dir_path.mkdir()
            for sample in samples:
                sample_file = JSONBased(
                    dir_path=self.samples_dir_path,
                    name=f'sample-{len(self.samples)}',
                    prefix='',
                )
                sample_file.write_json(sample)
                self.samples.append(sample_file)
