import zipfile
from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.content_graph.objects import base_content
from demisto_sdk.commands.content_graph.objects.agentix_flow import AgentixFlow
from demisto_sdk.commands.content_graph.parsers.agentix_flow import (
    AgentixFlowParser,
)
from TestSuite.pack import Pack

json = JSON_Handler()

FLOW_NAME = "PhishingTriage"
FLOW_DATA = {
    "id": "phishing-triage",
    "version": -1,
    "name": "Phishing triage",
    "description": "Triage a reported phishing email.",
    "marketplaces": ["platform"],
}


def _is_neo4j_property_value(value) -> bool:
    """Neo4j node properties must be primitives or (homogeneous) lists of primitives."""
    primitives = (str, int, float, bool, type(None))
    if isinstance(value, primitives):
        return True
    if isinstance(value, (list, tuple, set)):
        return all(isinstance(v, primitives) for v in value)
    return False


def _parse(flow_dir: Path) -> AgentixFlow:
    parser = AgentixFlowParser(
        flow_dir, list(MarketplaceVersions), pack_supported_modules=[]
    )
    return AgentixFlow.from_orm(parser)


def _dump(model: AgentixFlow, out_dir: Path) -> None:
    # The marketplace only affects the YAML; XSOAR avoids needing a pack object.
    model.dump(out_dir, MarketplaceVersions.XSOAR)


def test_agentix_flow_to_dict_has_only_neo4j_compatible_values(pack: Pack, monkeypatch):
    """
    Given:
        - An AgentixFlow (YAML + companion JSON + src/ code).
    When:
        - Converting the model to the dict used to create graph nodes.
    Then:
        - Every value is a type Neo4j accepts as a node property
          (regression: CypherTypeError in graph update), and no flow-engine
          or legacy ``definition`` data leaks into the node.
    """
    flow_path = Path(pack.create_agentix_flow(FLOW_NAME, FLOW_DATA).path)
    monkeypatch.setattr(base_content, "CONTENT_PATH", Path(pack.path).parent.parent)
    model = _parse(flow_path)

    node = model.to_dict()

    assert "definition" not in node
    assert "langgraph_version" not in node
    non_primitive = {
        k: v for k, v in node.items() if k != "path" and not _is_neo4j_property_value(v)
    }
    assert not non_primitive


def test_agentix_flow_folder_with_json_and_src_parses_only_the_yml(pack: Pack):
    """
    Given:
        - An AgentixFlow folder holding ``<F>.yml``, ``<F>_flow.json`` and ``src/``.
    When:
        - Parsing the folder, and running ``find_type`` on the companion JSON.
    Then:
        - The parser resolves the YAML, and the JSON is not classified as a
          content item.
    """
    flow = pack.create_agentix_flow(FLOW_NAME, FLOW_DATA)
    flow_dir = Path(flow.path).parent  # ``flow.path`` is the YAML file

    parser = AgentixFlowParser(
        flow_dir, list(MarketplaceVersions), pack_supported_modules=[]
    )

    assert parser.path == flow_dir / f"{FLOW_NAME}.yml"
    assert parser.get_path_with_suffix(".yml") == flow_dir / f"{FLOW_NAME}.yml"
    assert find_type(str(flow.flow_json_path)) is None


def test_agentix_flow_dump_writes_yml_json_and_zip(pack: Pack, tmp_path: Path):
    """
    Given:
        - An AgentixFlow with a companion JSON holding ``langgraph_version``, an
          author-set ``zip_path`` and an unknown key.
    When:
        - Dumping the flow.
    Then:
        - ``agentixflow-<F>.yml``, ``.json`` and ``.zip`` are written; the YAML
          has no ``definition``; the JSON keeps ``langgraph_version`` and the
          unknown key, and ``zip_path`` is overwritten with the zip file name.
    """
    flow = pack.create_agentix_flow(
        FLOW_NAME,
        FLOW_DATA,
        flow_json={
            "langgraph_version": "0.2.60",
            "zip_path": "author-value.zip",
            "future_key": {"a": 1},
        },
    )
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    assert sorted(p.name for p in out_dir.iterdir()) == [
        f"agentixflow-{FLOW_NAME}.json",
        f"agentixflow-{FLOW_NAME}.yml",
        f"agentixflow-{FLOW_NAME}.zip",
    ]
    assert "definition" not in (out_dir / f"agentixflow-{FLOW_NAME}.yml").read_text()
    assert json.loads((out_dir / f"agentixflow-{FLOW_NAME}.json").read_text()) == {
        "langgraph_version": "0.2.60",
        "zip_path": f"agentixflow-{FLOW_NAME}.zip",
        "future_key": {"a": 1},
    }


def test_agentix_flow_dump_zip_keeps_src_prefix_and_excludes_noise(
    pack: Pack, tmp_path: Path
):
    """
    Given:
        - A flow ``src/`` tree with nested code, tests, ``__pycache__``,
          dotfiles, test data and non-matching files.
    When:
        - Dumping the flow.
    Then:
        - The zip holds only the matching ``.py`` files, sorted, with arcnames
          relative to the flow folder (``src/`` prefix kept).
    """
    flow = pack.create_agentix_flow(
        FLOW_NAME,
        FLOW_DATA,
        src_files={
            "graph.py": "G = 1\n",
            "sub/x.py": "X = 1\n",
            "sub/__init__.py": "",
            "graph_test.py": "",
            "test_graph.py": "",
            "conftest.py": "",
            "sub/__pycache__/x.cpython-311.py": "",
            ".hidden.py": "",
            ".venv/lib.py": "",
            "test_data/sample.py": "",
            "README.md": "",
        },
    )
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    with zipfile.ZipFile(out_dir / f"agentixflow-{FLOW_NAME}.zip") as zf:
        names = zf.namelist()
        assert zf.read("src/sub/x.py") == b"X = 1\n"
    assert names == ["src/graph.py", "src/sub/__init__.py", "src/sub/x.py"]


def test_agentix_flow_dump_zip_is_deterministic(pack: Pack, tmp_path: Path):
    """
    Given:
        - An AgentixFlow with code under ``src/``.
    When:
        - Dumping it twice, with the source mtimes changed in between.
    Then:
        - Both zips are byte-identical.
    """
    flow = pack.create_agentix_flow(
        FLOW_NAME, FLOW_DATA, src_files={"graph.py": "G = 1\n", "sub/x.py": "X\n"}
    )
    model = _parse(Path(flow.path))

    _dump(model, tmp_path / "a")
    for py in flow.code_dir.rglob("*.py"):
        py.touch()
    _dump(model, tmp_path / "b")

    zip_name = f"agentixflow-{FLOW_NAME}.zip"
    assert (tmp_path / "a" / zip_name).read_bytes() == (
        tmp_path / "b" / zip_name
    ).read_bytes()


@pytest.mark.parametrize(
    "flow_json_text, match",
    [
        pytest.param(None, "not found", id="missing json"),
        pytest.param("{not json", "invalid JSON", id="invalid json"),
        pytest.param("[1, 2]", "JSON object", id="json is not an object"),
        pytest.param("{}", "langgraph_version", id="missing langgraph_version"),
        pytest.param(
            '{"langgraph_version": ""}', "langgraph_version", id="empty version"
        ),
        pytest.param(
            '{"langgraph_version": 1}', "langgraph_version", id="non-string version"
        ),
    ],
)
def test_agentix_flow_dump_raises_on_bad_flow_json(
    pack: Pack, tmp_path: Path, flow_json_text, match: str
):
    """
    Given:
        - An AgentixFlow whose companion JSON is missing or invalid.
    When:
        - Dumping the flow.
    Then:
        - A ``ValueError`` is raised, so the build fails loudly.
    """
    flow = pack.create_agentix_flow(FLOW_NAME, FLOW_DATA)
    if flow_json_text is None:
        flow.flow_json_path.unlink()
    else:
        flow.flow_json_path.write_text(flow_json_text)

    with pytest.raises(ValueError, match=match):
        _dump(_parse(Path(flow.path)), tmp_path / "out")


@pytest.mark.parametrize(
    "src_files",
    [
        pytest.param(None, id="no src dir"),
        pytest.param({"graph_test.py": "", "README.md": ""}, id="no matching files"),
    ],
)
def test_agentix_flow_dump_raises_when_src_has_no_code(
    pack: Pack, tmp_path: Path, src_files
):
    """
    Given:
        - An AgentixFlow whose ``src/`` is missing or has no matching files.
    When:
        - Dumping the flow.
    Then:
        - A ``ValueError`` is raised, so the build fails loudly.
    """
    flow = pack.create_agentix_flow(FLOW_NAME, FLOW_DATA, src_files={"graph.py": ""})
    (flow.code_dir / "graph.py").unlink()
    flow.code_dir.rmdir()
    if src_files is not None:
        flow.build(src_files=src_files)

    with pytest.raises(ValueError, match="src"):
        _dump(_parse(Path(flow.path)), tmp_path / "out")
