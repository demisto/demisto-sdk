from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.handlers import JSON_Handler
from TestSuite.yml import YAML, yaml

json = JSON_Handler()

DEFAULT_FLOW_ASSETS_DIR = Path(__file__).parent / "assets" / "default_agentix_flow"


class AgentixFlow(YAML):
    """A TestSuite representation of an AgentixFlow content item.

    Each flow lives in its own folder under ``AgentixFlows/`` and contains:
    - ``<FlowName>.yml``: the content item (top-level ``id`` and ``version``,
      no ``commonfields`` block);
    - ``<FlowName>_flow.json``: the flow-engine metadata (``langgraph_version``);
    - ``src/**``: the LangGraph code, zipped at dump time.
    """

    FLOW_JSON_SUFFIX = "_flow.json"
    CODE_DIR = "src"

    def __init__(self, tmpdir: Path, name: str, repo):
        # Create directory for the flow
        self._tmpdir_flow_path = tmpdir / name
        self._tmpdir_flow_path.mkdir(exist_ok=True)

        # Save entities
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        self.path = str(self._tmpdir_flow_path)

        super().__init__(
            tmp_path=self._tmpdir_flow_path / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

    @property
    def flow_json_path(self) -> Path:
        return self._tmpdir_flow_path / f"{self.name}{self.FLOW_JSON_SUFFIX}"

    @property
    def code_dir(self) -> Path:
        return self._tmpdir_flow_path / self.CODE_DIR

    def build(
        self,
        yml: Optional[dict] = None,
        flow_json: Optional[dict] = None,
        src_files: Optional[Dict[str, str]] = None,
    ):
        """Writes not None objects to files.

        Args:
            yml: The ``<FlowName>.yml`` content.
            flow_json: The ``<FlowName>_flow.json`` content.
            src_files: Mapping of a path relative to ``src/`` to its content,
                e.g. ``{"graph.py": "...", "nodes/triage.py": "..."}``.
        """
        if yml is not None:
            self.write_dict(yml)
        if flow_json is not None:
            self.flow_json_path.write_text(json.dumps(flow_json, indent=4))
        for rel_path, content in (src_files or {}).items():
            file_path = self.code_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    @staticmethod
    def default_flow_json() -> dict:
        return json.loads(
            (DEFAULT_FLOW_ASSETS_DIR / "agentix_flow-sample_flow.json").read_text()
        )

    @staticmethod
    def default_src_files() -> Dict[str, str]:
        return {"graph.py": (DEFAULT_FLOW_ASSETS_DIR / "src" / "graph.py").read_text()}

    def create_default_agentix_flow(
        self,
        name: str = "Sample Agentix Flow",
        flow_id: str = "sample-agentix-flow",
        flow_json: Optional[dict] = None,
        src_files: Optional[Dict[str, str]] = None,
    ):
        """Creates a new agentix flow with basic data.

        Args:
            name: The name of the new flow, default is "Sample Agentix Flow".
            flow_id: The ID of the new flow, default is "sample-agentix-flow".
            flow_json: Overrides the default ``<FlowName>_flow.json`` content.
            src_files: Overrides the default ``src/`` files.
        """
        with open(DEFAULT_FLOW_ASSETS_DIR / "agentix_flow-sample.yml") as yml_file:
            yml = yaml.load(yml_file)
        yml["id"] = flow_id
        yml["name"] = name
        self.build(
            yml=yml,
            flow_json=flow_json if flow_json is not None else self.default_flow_json(),
            src_files=src_files if src_files is not None else self.default_src_files(),
        )
