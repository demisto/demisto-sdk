from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.content_graph.objects import base_content
from demisto_sdk.commands.content_graph.objects.agentix_flow import AgentixFlow
from demisto_sdk.commands.content_graph.parsers.agentix_flow import (
    AgentixFlowParser,
)
from TestSuite.pack import Pack

FLOW_DATA = {
    "id": "phishing-triage",
    "version": -1,
    "name": "Phishing triage",
    "description": "Triage a reported phishing email.",
    "marketplaces": ["platform"],
    "definition": {
        "schema_version": "0.1",
        "flow_id": "phishing-triage",
        "trigger": {"type": "phishing-reported"},
        "nodes": [{"id": "start", "type": "agent", "config": {"agent": "x"}}],
    },
}


def _create_flow(pack: Pack) -> Path:
    flow_dir = Path(pack.path) / "AgentixFlows" / "PhishingTriage"
    flow_dir.mkdir(parents=True)
    flow_path = flow_dir / "PhishingTriage.yml"
    with flow_path.open("w") as f:
        yaml.dump(FLOW_DATA, f)
    return flow_path


def _is_neo4j_property_value(value) -> bool:
    """Neo4j node properties must be primitives or (homogeneous) lists of primitives."""
    primitives = (str, int, float, bool, type(None))
    if isinstance(value, primitives):
        return True
    if isinstance(value, (list, tuple, set)):
        return all(isinstance(v, primitives) for v in value)
    return False


def test_agentix_flow_to_dict_has_only_neo4j_compatible_values(pack: Pack, monkeypatch):
    """
    Given:
        - An AgentixFlow whose ``definition`` is a nested map.
    When:
        - Converting the model to the dict used to create graph nodes.
    Then:
        - ``definition`` is not part of the node, and every value is a type Neo4j
          accepts as a node property (regression: CypherTypeError in graph update).
    """
    flow_path = _create_flow(pack)
    monkeypatch.setattr(base_content, "CONTENT_PATH", Path(pack.path).parent.parent)
    parser = AgentixFlowParser(
        flow_path, list(MarketplaceVersions), pack_supported_modules=[]
    )
    model = AgentixFlow.from_orm(parser)

    node = model.to_dict()

    assert "definition" not in node
    non_primitive = {
        k: v for k, v in node.items() if k != "path" and not _is_neo4j_property_value(v)
    }
    assert not non_primitive


def test_agentix_flow_definition_kept_on_model_and_in_file_data(pack: Pack):
    """
    Given:
        - An AgentixFlow with a ``definition`` block.
    When:
        - Parsing it into a model and reading its file data (used for packaging).
    Then:
        - ``definition`` is still available on the model and in the uploaded data.
    """
    flow_path = _create_flow(pack)
    parser = AgentixFlowParser(
        flow_path, list(MarketplaceVersions), pack_supported_modules=[]
    )
    model = AgentixFlow.from_orm(parser)

    assert model.definition == FLOW_DATA["definition"]
    assert model.data["definition"] == FLOW_DATA["definition"]
