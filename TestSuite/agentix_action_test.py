from pathlib import Path

from TestSuite.yml import YAML


class AgentixActionTest(YAML):
    def __init__(
        self,
        agentix_tests_dir: Path,
        name: str,
        repo,
    ):
        super().__init__(agentix_tests_dir / f"{name}.yml", repo.path)
