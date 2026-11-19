"""Tests verifying that the CI-injected ``is_content_private`` (item level) and
``is_content_private_only`` (pack level) keys are stripped **unconditionally**
(not gated on ``strip_internal``) from everything the new content-graph path
uploads or writes to artifacts."""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.common.constants import (
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.tools import get_file, get_json
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.list import List as ListObject
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.prepare_content.list_unifier import ListUnifier
from demisto_sdk.commands.prepare_content.rule_unifier import RuleUnifier

BOTH_KEYS = (IS_CONTENT_PRIVATE_KEY, IS_CONTENT_PRIVATE_ONLY_KEY)


def _assert_no_flag_in_files(root: Path) -> None:
    """Walk every file under ``root`` and assert neither key name appears in it."""
    files = [f for f in root.rglob("*") if f.is_file()]
    assert files, f"test premise: nothing was written under {root}"
    for file in files:
        text = file.read_text(errors="ignore")
        for key in BOTH_KEYS:
            assert key not in text, f"{key} leaked into {file}"


def _build_script(path: Path) -> Script:
    return Script.construct(  # type: ignore[call-arg]
        object_id="MyScript",
        name="MyScript",
        path=path,
        marketplaces=[MarketplaceVersions.XSOAR],
        tags=[],
        skip_prepare=[],
        is_test=False,
        type="python",
        subtype="python3",
        docker_image="",
        is_llm=False,
        is_internal=False,
        internal=False,
        source="",
        is_unified=False,
    )


def _build_classifier(path: Path) -> Classifier:
    return Classifier.construct(  # type: ignore[call-arg]
        object_id="MyClassifier",
        content_type=ContentType.CLASSIFIER,
        name="MyClassifier",
        path=path,
        marketplaces=[MarketplaceVersions.XSOAR],
        fromversion="6.0.0",
        toversion="99.99.99",
        display_name="MyClassifier",
    )


# ---------------------------------------------------------------------------
# ContentItem.prepare_for_upload (YAML and JSON items).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strip_internal", [False, True])
def test_content_item_prepare_for_upload_strips_flag_from_json(
    tmp_path: Path, strip_internal: bool
):
    """
    Given:
        - A JSON content item (classifier) carrying ``is_content_private: true``.
    When:
        - ``ContentItem.prepare_for_upload`` is called, with and without ``strip_internal``.
    Then:
        - The flag is removed in both cases and other keys are preserved.
    """
    path = tmp_path / "classifier-MyClassifier.json"
    path.write_text(
        json.dumps(
            {
                "id": "MyClassifier",
                "type": "classification",
                IS_CONTENT_PRIVATE_KEY: True,
            }
        )
    )

    data = _build_classifier(path).prepare_for_upload(strip_internal=strip_internal)

    assert IS_CONTENT_PRIVATE_KEY not in data
    assert data["id"] == "MyClassifier"


def test_content_item_prepare_for_upload_strips_flag_from_yaml(tmp_path: Path, mocker):
    """
    Given:
        - A YAML content item (script) carrying ``is_content_private: true``.
    When:
        - ``IntegrationScript.prepare_for_upload`` runs the regular (non unify_only) path,
          so ``ContentItem.prepare_for_upload`` is reached.
    Then:
        - The flag is not in the prepared data.
    """
    path = tmp_path / "script-MyScript.yml"
    with path.open("w") as f:
        yaml.dump(
            {"name": "MyScript", "type": "python", IS_CONTENT_PRIVATE_KEY: True}, f
        )
    mocker.patch.object(
        IntegrationScriptUnifier, "unify", side_effect=lambda _p, data, *_a, **_k: data
    )

    data = _build_script(path).prepare_for_upload()

    assert IS_CONTENT_PRIVATE_KEY not in data
    assert data["name"] == "MyScript"


def test_content_item_prepare_for_upload_does_not_pop_top_level_keys_from_cached_data(
    tmp_path: Path,
):
    """
    Given:
        - A JSON item with the flag, whose ``data`` is cached and shared by ``get_file`` (lru_cache).
    When:
        - A regular (non unify_only) ``prepare_for_upload`` runs, twice.
    Then:
        - ``item.data`` still contains the flag (the pop ran on a copy).
        - Both calls return identical output.
    """
    path = tmp_path / "classifier-MyClassifier.json"
    path.write_text(json.dumps({"id": "MyClassifier", IS_CONTENT_PRIVATE_KEY: True}))
    item = _build_classifier(path)

    first = item.prepare_for_upload()
    second = item.prepare_for_upload()

    assert IS_CONTENT_PRIVATE_KEY in item.data
    assert IS_CONTENT_PRIVATE_KEY not in first
    assert first == second


# ---------------------------------------------------------------------------
# IntegrationScript: both the unify_only branch and the regular path.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unify_only", [False, True])
def test_integration_script_prepare_for_upload_strips_flag(
    tmp_path: Path, mocker, unify_only: bool
):
    """
    Given:
        - A script YAML carrying ``is_content_private``.
    When:
        - ``IntegrationScript.prepare_for_upload`` runs with and without ``unify_only``.
    Then:
        - The flag is stripped in both branches.
    """
    path = tmp_path / "script-MyScript.yml"
    with path.open("w") as f:
        yaml.dump(
            {"name": "MyScript", "type": "python", IS_CONTENT_PRIVATE_KEY: True}, f
        )
    mocker.patch.object(
        IntegrationScriptUnifier, "unify", side_effect=lambda _p, data, *_a, **_k: data
    )

    script = _build_script(path)
    data = script.prepare_for_upload(unify_only=unify_only)

    assert IS_CONTENT_PRIVATE_KEY not in data
    assert IS_CONTENT_PRIVATE_KEY not in script.unified_data
    if unify_only:
        # The bypass branch works on a copy, so the shared (cached) source data keeps the flag.
        assert IS_CONTENT_PRIVATE_KEY in script.data


# ---------------------------------------------------------------------------
# unify_only branches that skip ``super().prepare_for_upload``.
# ---------------------------------------------------------------------------


def test_list_prepare_for_upload_unify_only_strips_flag(tmp_path: Path, mocker):
    """
    Given:
        - A list JSON carrying the flag.
    When:
        - ``List.prepare_for_upload`` runs with ``unify_only=True`` (and with the regular path).
    Then:
        - The flag is stripped in both, and the ``unify_only`` branch does not mutate the cached ``data``.
    """
    path = tmp_path / "list-MyList.json"
    path.write_text(
        json.dumps(
            {
                "id": "MyList",
                "data": "a",
                "allRead": False,
                IS_CONTENT_PRIVATE_KEY: True,
            }
        )
    )
    mocker.patch.object(ListUnifier, "unify", side_effect=lambda _p, data, **_k: data)
    item = ListObject.construct(  # type: ignore[call-arg]
        object_id="MyList",
        content_type=ContentType.LIST,
        name="MyList",
        path=path,
        marketplaces=[MarketplaceVersions.XSOAR],
        is_unified=False,
    )

    assert IS_CONTENT_PRIVATE_KEY not in item.prepare_for_upload(unify_only=True)
    assert IS_CONTENT_PRIVATE_KEY in item.data
    assert IS_CONTENT_PRIVATE_KEY not in item.prepare_for_upload()


@pytest.mark.parametrize("rule_class", [ParsingRule, ModelingRule])
@pytest.mark.parametrize("unify_only", [False, True])
def test_xsiam_rules_prepare_for_upload_strip_flag(
    tmp_path: Path, mocker, rule_class, unify_only: bool
):
    """
    Given:
        - A parsing/modeling rule YAML carrying the flag.
    When:
        - ``prepare_for_upload`` runs with and without ``unify_only``.
    Then:
        - The flag is stripped, and the ``unify_only`` branch does not mutate the cached ``data``.
    """
    path = tmp_path / "rule.yml"
    with path.open("w") as f:
        yaml.dump({"name": "rule", "rules": "", IS_CONTENT_PRIVATE_KEY: True}, f)
    mocker.patch.object(RuleUnifier, "unify", side_effect=lambda _p, data, _m: data)
    item = rule_class.construct(  # type: ignore[call-arg]
        object_id="rule",
        name="rule",
        path=path,
        marketplaces=[MarketplaceVersions.MarketplaceV2],
    )

    data = item.prepare_for_upload(
        MarketplaceVersions.MarketplaceV2, unify_only=unify_only
    )

    assert IS_CONTENT_PRIVATE_KEY not in data
    if unify_only:
        assert IS_CONTENT_PRIVATE_KEY in item.data


# ---------------------------------------------------------------------------
# pack_metadata.json copied by Pack._dump_pack_metadata.
# ---------------------------------------------------------------------------


def _call_dump_pack_metadata(
    source: Path, destination: Path, strip_internal: bool = False
) -> None:
    Pack._dump_pack_metadata(
        MagicMock(),
        source,
        destination,
        MarketplaceVersions.XSOAR,
        strip_internal=strip_internal,
    )


@pytest.mark.parametrize("strip_internal", [False, True])
def test_dump_pack_metadata_strips_pack_flag_regardless_of_strip_internal(
    tmp_path: Path, strip_internal: bool
):
    """
    Given:
        - A ``pack_metadata.json`` carrying ``is_content_private_only: true`` and ``internal: true``.
    When:
        - ``Pack._dump_pack_metadata`` runs with ``strip_internal`` False and True.
    Then:
        - ``is_content_private_only`` is removed in both cases (not gated on ``strip_internal``),
          while ``internal`` is only removed when ``strip_internal`` is true.
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir()
    source.write_text(
        json.dumps(
            {
                "name": "TestPack",
                "internal": True,
                IS_CONTENT_PRIVATE_ONLY_KEY: True,
                "currentVersion": "1.0.0",
            }
        )
    )

    _call_dump_pack_metadata(source, destination, strip_internal=strip_internal)

    written: Dict[str, Any] = get_json(destination)
    assert IS_CONTENT_PRIVATE_ONLY_KEY not in written
    assert ("internal" in written) is (not strip_internal)
    assert written["name"] == "TestPack"
    # The source file (and its cached parse) keeps the flag.
    assert get_json(source)[IS_CONTENT_PRIVATE_ONLY_KEY] is True


# ---------------------------------------------------------------------------
# metadata.json generated by Pack.dump_metadata.
# ---------------------------------------------------------------------------


def _build_pack(path: Path, **extra) -> Pack:
    extra[IS_CONTENT_PRIVATE_ONLY_KEY] = True
    return Pack(
        object_id="TestPack",
        content_type=ContentType.PACK,
        node_id="Pack:TestPack",
        path=path,
        name="TestPack",
        display_name="TestPack",
        marketplaces=[MarketplaceVersions.XSOAR],
        current_version="1.0.0",
        description="desc",
        created="2024-01-01T00:00:00Z",
        support="xsoar",
        author="Cortex XSOAR",
        certification="certified",
        hidden=False,
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems={},
        **extra,
    )


@pytest.mark.parametrize("strip_internal", [False, True])
def test_dump_metadata_never_contains_pack_flag(tmp_path: Path, strip_internal: bool):
    """
    Given:
        - A Pack flagged as ``is_content_private_only``.
    When:
        - ``Pack.dump_metadata`` writes ``metadata.json``.
    Then:
        - The key is not in the file, with and without ``strip_internal``.
    """
    pack = _build_pack(tmp_path)
    destination = tmp_path / "metadata.json"

    pack.dump_metadata(
        destination, MarketplaceVersions.XSOAR, strip_internal=strip_internal
    )

    assert IS_CONTENT_PRIVATE_ONLY_KEY not in destination.read_text()


# ---------------------------------------------------------------------------
# End to end: Pack.dump of a tmp pack with a flagged item and flagged pack_metadata.json.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strip_internal", [False, True])
def test_pack_dump_end_to_end_leaves_no_flag_in_output(
    tmp_path: Path, strip_internal: bool
):
    """
    Given:
        - A pack on disk with a flagged classifier and a flagged pack_metadata.json.
    When:
        - ``Pack.dump`` writes the pack (the entry point of upload, zip and prepare-content).
    Then:
        - No file in the output contains either key name, and the regular fields survive.
    """
    pack_dir = tmp_path / "Packs" / "TestPack"
    pack_dir.mkdir(parents=True)
    (pack_dir / "README.md").write_text("readme")
    (pack_dir / "pack_metadata.json").write_text(
        json.dumps(
            {
                "name": "TestPack",
                "currentVersion": "1.0.0",
                IS_CONTENT_PRIVATE_ONLY_KEY: True,
            }
        )
    )
    classifier_path = pack_dir / "Classifiers" / "classifier-MyClassifier.json"
    classifier_path.parent.mkdir()
    classifier_path.write_text(
        json.dumps(
            {
                "id": "MyClassifier",
                "type": "classification",
                IS_CONTENT_PRIVATE_KEY: True,
            }
        )
    )
    pack = _build_pack(pack_dir)
    pack.content_items.classifier.append(_build_classifier(classifier_path))
    output = tmp_path / "out"

    pack.dump(output, MarketplaceVersions.XSOAR, strip_internal=strip_internal)

    _assert_no_flag_in_files(output)
    assert get_file(output / "pack_metadata.json")["name"] == "TestPack"
    dumped_classifier = next((output / "Classifiers").iterdir())
    assert get_json(dumped_classifier)["id"] == "MyClassifier"
