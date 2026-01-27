from pathlib import Path
from typing import Optional

from TestSuite.json_based import JSONBased


from TestSuite.yml import YAML


class AgentixTest(YAML):
    def __init__(
        self,
        agentix_tests_dir: Path,
        name: str,
        repo,
    ):
        super().__init__(agentix_tests_dir / f"{name}.yml", repo.path)
