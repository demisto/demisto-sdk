import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from demisto_sdk.commands.common.constants import (
    DEFAULT_AGENTIX_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import find_type, get_file
from demisto_sdk.commands.content_graph.objects import base_content, content_item
from demisto_sdk.commands.content_graph.objects.agentix_flow import AgentixFlow
from demisto_sdk.commands.content_graph.parsers.agentix_flow import (
    AgentixFlowParser,
)
from TestSuite.pack import Pack

json = JSON_Handler()

FLOW_NAME = "PhishingTriage"
FLOW_DATA: Dict[str, Any] = {
    "id": "phishing-triage",
    "version": -1,
    "name": "Phishing triage",
    "description": "Triage a reported phishing email.",
    "marketplaces": ["platform"],
}
SHIPPED_YML = f"agentixflow-{FLOW_NAME}.yml"
SHIPPED_JSON = f"agentixflow-{FLOW_NAME}.json"
SHIPPED_ZIP = f"agentixflow-{FLOW_NAME}.zip"


@pytest.fixture(autouse=True)
def _content_path_is_the_test_repo(pack: Pack, monkeypatch):
    """Resolve the flow's pack (and its ``supportedModules``) from the test repo."""
    repo_path = Path(pack.path).parent.parent
    monkeypatch.setattr(content_item, "CONTENT_PATH", repo_path)
    monkeypatch.setattr(base_content, "CONTENT_PATH", repo_path)


def _is_neo4j_property_value(value) -> bool:
    """Neo4j node properties must be primitives or (homogeneous) lists of primitives."""
    primitives = (str, int, float, bool, type(None))
    if isinstance(value, primitives):
        return True
    if isinstance(value, (list, tuple, set)):
        return all(isinstance(v, primitives) for v in value)
    return False


def _parse(
    flow_dir: Path, pack_supported_modules: Optional[List[str]] = None
) -> AgentixFlow:
    parser = AgentixFlowParser(
        flow_dir,
        list(MarketplaceVersions),
        pack_supported_modules=pack_supported_modules or [],
    )
    return AgentixFlow.from_orm(parser)


def _dump(model: AgentixFlow, out_dir: Path) -> None:
    # Flows only ship to the platform marketplace.
    model.dump(out_dir, MarketplaceVersions.PLATFORM)


def _shipped(out_dir: Path) -> Tuple[dict, dict]:
    """The shipped (YAML dict, JSON dict) pair."""
    shipped_yml = get_file(out_dir / SHIPPED_YML, keep_order=True)
    assert isinstance(shipped_yml, dict)
    return shipped_yml, json.loads((out_dir / SHIPPED_JSON).read_text())


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
        - An AgentixFlow with a companion JSON holding only ``langgraph_version``.
    When:
        - Dumping the flow.
    Then:
        - ``agentixflow-<F>.yml``, ``.json`` and ``.zip`` are written; the YAML
          has no ``definition``; the JSON holds the generated content fields,
          then ``langgraph_version``, then ``zip_path`` (the zip file name).
    """
    flow = pack.create_agentix_flow(
        FLOW_NAME, FLOW_DATA, flow_json={"langgraph_version": "0.2.60"}
    )
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    assert sorted(p.name for p in out_dir.iterdir()) == [
        SHIPPED_JSON,
        SHIPPED_YML,
        SHIPPED_ZIP,
    ]
    assert "definition" not in (out_dir / SHIPPED_YML).read_text()
    assert json.loads((out_dir / SHIPPED_JSON).read_text()) == {
        "id": "phishing-triage",
        "version": -1,
        "name": "Phishing triage",
        "description": "Triage a reported phishing email.",
        "fromversion": DEFAULT_AGENTIX_ITEM_FROM_VERSION,
        "toversion": DEFAULT_CONTENT_ITEM_TO_VERSION,
        "marketplaces": ["platform"],
        "langgraph_version": "0.2.60",
        "zip_path": SHIPPED_ZIP,
    }


# The keys the JSON adds when the shipped YAML leaves them out, in this order
# (parser-defaulted versions, then the stripped effective modules).
_FILLABLE_KEYS = ("fromversion", "toversion", "supportedModules")


@pytest.mark.parametrize(
    "yml, pack_modules",
    [
        pytest.param(
            {
                "id": "phishing-triage",
                "version": -1,
                "name": "Phishing triage",
                "description": "Triage phishing in Cortex XSOAR.",
                "tags": ["phishing"],
                "category": "Email",
                "disabled": False,
                "internal": False,
                "fromversion": "8.13.0",
                "toversion": "9.0.0",
                "supportedModules": ["agentix", "xsiam"],
                "marketplaces": ["platform"],
                "supportedFeatures": ["feature-a"],
            },
            ["agentix", "xsiam", "edr"],
            id="every field set (modules kept in yml)",
        ),
        pytest.param(
            {**FLOW_DATA, "supportedModules": ["agentix"]},
            ["agentix"],
            id="minimal yml (defaults and stripped modules filled in)",
        ),
    ],
)
def test_agentix_flow_dump_json_content_is_the_shipped_yaml_plus_missing_values(
    pack: Pack, tmp_path: Path, yml: dict, pack_modules: List[str]
):
    """
    Given:
        - A flow YAML (one with every field set and a "Cortex XSOAR" reference
          the platform marketplace rewrites, one minimal).
    When:
        - Dumping the flow for the platform marketplace.
    Then:
        - The JSON starts with the shipped YAML, key for key and value for
          value, followed by any missing ``fromversion`` / ``toversion`` /
          ``supportedModules`` (in that order), then ``langgraph_version``
          and ``zip_path``.
    """
    pack.pack_metadata.update({"supportedModules": pack_modules})
    flow = pack.create_agentix_flow(
        FLOW_NAME, yml, flow_json={"langgraph_version": "0.2.60"}
    )
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path), pack_modules), out_dir)

    shipped_yml, shipped_json = _shipped(out_dir)
    filled = [k for k in _FILLABLE_KEYS if k not in shipped_yml]
    assert list(shipped_json) == [
        *shipped_yml,
        *filled,
        "langgraph_version",
        "zip_path",
    ]
    assert {k: shipped_json[k] for k in shipped_yml} == dict(shipped_yml)
    assert "Cortex XSOAR" not in shipped_json["description"]


def test_agentix_flow_dump_json_keeps_unknown_yaml_keys(pack: Pack, tmp_path: Path):
    """
    Given:
        - A flow YAML with a top-level key not (yet) in the schema.
    When:
        - Dumping the flow.
    Then:
        - The key ships in the JSON with its YAML value, as there is no field
          list to filter it out.
    """
    flow = pack.create_agentix_flow(FLOW_NAME, {**FLOW_DATA, "futureField": [1, 2]})
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    _, shipped_json = _shipped(out_dir)
    assert shipped_json["futureField"] == [1, 2]


def test_agentix_flow_dump_json_applies_version_defaults(pack: Pack, tmp_path: Path):
    """
    Given:
        - A flow YAML without ``fromversion`` / ``toversion``.
    When:
        - Dumping the flow.
    Then:
        - The JSON holds the model defaults (the Agentix from-version and
          the default content to-version); the shipped YAML is unchanged.
    """
    flow = pack.create_agentix_flow(FLOW_NAME, FLOW_DATA)
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    shipped_yml, shipped_json = _shipped(out_dir)
    assert shipped_json["fromversion"] == DEFAULT_AGENTIX_ITEM_FROM_VERSION
    assert shipped_json["toversion"] == DEFAULT_CONTENT_ITEM_TO_VERSION
    assert "fromversion" not in shipped_yml
    assert "toversion" not in shipped_yml


@pytest.mark.parametrize(
    "item_modules, pack_modules, parse_with_pack_modules, expected_json, expected_yml",
    [
        pytest.param(
            None, ["agentix"], True, ["agentix"], None, id="inherited from pack"
        ),
        pytest.param(
            None,
            ["agentix"],
            False,
            ["agentix"],
            None,
            id="inherited from pack (standalone parse)",
        ),
        pytest.param(
            ["agentix"],
            ["agentix"],
            True,
            ["agentix"],
            None,
            id="stripped from yml (equals pack)",
        ),
        pytest.param(
            ["agentix"],
            ["agentix", "edr"],
            True,
            ["agentix"],
            ["agentix"],
            id="item subset of pack (kept in yml)",
        ),
        pytest.param(None, None, True, None, None, id="neither defines it"),
    ],
)
def test_agentix_flow_dump_json_has_effective_supported_modules(
    pack: Pack,
    tmp_path: Path,
    item_modules,
    pack_modules,
    parse_with_pack_modules: bool,
    expected_json,
    expected_yml,
):
    """
    Given:
        - Item and/or pack ``supportedModules`` combinations.
    When:
        - Dumping the flow for the platform marketplace.
    Then:
        - The JSON holds the effective modules (item, else pack; omitted when
          neither defines them), even when the YAML has them stripped.
    """
    if pack_modules is not None:
        pack.pack_metadata.update({"supportedModules": pack_modules})
    yml = dict(FLOW_DATA)
    if item_modules is not None:
        yml["supportedModules"] = item_modules
    flow = pack.create_agentix_flow(FLOW_NAME, yml)
    out_dir = tmp_path / "out"

    _dump(
        _parse(Path(flow.path), pack_modules if parse_with_pack_modules else None),
        out_dir,
    )

    shipped_yml, shipped_json = _shipped(out_dir)
    assert shipped_json.get("supportedModules") == expected_json
    assert shipped_yml.get("supportedModules") == expected_yml


def test_agentix_flow_dump_json_generated_fields_override_author_keys(
    pack: Pack, tmp_path: Path, mocker
):
    """
    Given:
        - A companion JSON that also sets content fields (``id``, ``tags``),
          ``zip_path`` and an unknown key.
    When:
        - Dumping the flow.
    Then:
        - The generated values win (``tags`` is dropped as the YAML has none),
          a warning names each overridden key, and the unknown key and
          ``langgraph_version`` are kept in their order before ``zip_path``.
    """
    from demisto_sdk.commands.content_graph.objects import agentix_flow

    warning = mocker.patch.object(agentix_flow.logger, "warning")
    flow = pack.create_agentix_flow(
        FLOW_NAME,
        FLOW_DATA,
        flow_json={
            "id": "wrong",
            "langgraph_version": "0.2.60",
            "tags": ["author"],
            "future_key": {"a": 1},
            "zip_path": "author-value.zip",
        },
    )
    out_dir = tmp_path / "out"

    _dump(_parse(Path(flow.path)), out_dir)

    _, shipped_json = _shipped(out_dir)
    assert shipped_json["id"] == "phishing-triage"
    assert "tags" not in shipped_json
    assert shipped_json["zip_path"] == SHIPPED_ZIP
    assert list(shipped_json)[-3:] == ["langgraph_version", "future_key", "zip_path"]
    assert shipped_json["future_key"] == {"a": 1}
    warned = " ".join(str(c.args[0]) for c in warning.call_args_list)
    for key in ("'id'", "'tags'", "'zip_path'"):
        assert key in warned
    assert "langgraph_version" not in warned
    assert "future_key" not in warned


def test_agentix_flow_dump_json_and_yml_are_byte_identical_across_dumps(
    pack: Pack, tmp_path: Path
):
    """
    Given:
        - An AgentixFlow.
    When:
        - Dumping it twice.
    Then:
        - The shipped JSON and YAML are byte-identical.
    """
    pack.pack_metadata.update({"supportedModules": ["agentix"]})
    flow = pack.create_agentix_flow(
        FLOW_NAME, FLOW_DATA, flow_json={"langgraph_version": "0.2.60", "k": 1}
    )
    model = _parse(Path(flow.path), ["agentix"])

    _dump(model, tmp_path / "a")
    _dump(model, tmp_path / "b")

    for name in (SHIPPED_JSON, SHIPPED_YML):
        assert (tmp_path / "a" / name).read_bytes() == (
            tmp_path / "b" / name
        ).read_bytes()


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

    assert (tmp_path / "a" / SHIPPED_ZIP).read_bytes() == (
        tmp_path / "b" / SHIPPED_ZIP
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
