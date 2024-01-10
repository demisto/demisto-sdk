from __future__ import annotations

from typing import TYPE_CHECKING

from demisto_sdk.commands.common.constants import SAMPLES_DIR
from TestSuite.json_based import JSONBased
from TestSuite.test_suite_base import TestSuiteBase
from demisto_sdk.commands.common.tools import set_value

if TYPE_CHECKING:
    from TestSuite.repo import Repo

from pathlib import Path

from demisto_sdk.commands.common.handlers import YAML_Handler
from TestSuite.file import File
from TestSuite.yml import YAML

yaml = YAML_Handler()


class Rule(TestSuiteBase):
    def __init__(
        self,
        tmpdir: Path,
        name: str,
        repo: Repo,
    ):
        self.name = name
        self._repo = repo
        self.repo_path = repo.path

        self._tmpdir_rule_path = tmpdir / f"{self.name}"
        self._tmpdir_rule_path.mkdir()

        self.path = str(self._tmpdir_rule_path)
        self.yml = YAML(self._tmpdir_rule_path / f"{self.name}.yml", self._repo.path)
        self.rules = File(self._tmpdir_rule_path / f"{self.name}.xif", self._repo.path)
        self.schema = JSONBased(self._tmpdir_rule_path, f"{self.name}_schema", "")
        self.testdata = JSONBased(self._tmpdir_rule_path, f"{self.name}_testdata", "")

        self.samples: list[JSONBased] = []
        self.samples_dir_path = tmpdir / self.name / SAMPLES_DIR
        super().__init__(self._tmpdir_rule_path)

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
            self.schema.write_json(schema)
        if samples:
            self.samples_dir_path.mkdir()
            for sample in samples:
                sample_file = JSONBased(
                    dir_path=self.samples_dir_path,
                    name=f"sample-{len(self.samples)}",
                    prefix="",
                )
                sample_file.write_json(sample)
                self.samples.append(sample_file)

    def set_data(self, **key_path_to_val):
        yml_contents = self.yml.read_dict()
        for key_path, val in key_path_to_val.items():
            set_value(yml_contents, key_path, val)
        self.yml.write_dict(yml_contents)
        self.clear_from_path_cache()