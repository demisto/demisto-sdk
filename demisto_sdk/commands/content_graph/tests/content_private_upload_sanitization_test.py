from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.common.constants import (
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.tools import get_json
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


def _build_pack(path: Path) -> Pack:
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
        is_content_private_only=True,
    )


def test_content_item_prepare_for_upload_strips_flag_without_mutating_cached_data(
    tmp_path: Path,
):
    path = tmp_path / "classifier-MyClassifier.json"
    path.write_text(json.dumps({"id": "MyClassifier", IS_CONTENT_PRIVATE_KEY: True}))
    item = _build_classifier(path)

    assert item.prepare_for_upload() == {"id": "MyClassifier"}
    assert IS_CONTENT_PRIVATE_KEY in item.data


def test_integration_script_unify_only_strips_flag(tmp_path: Path, mocker):
    path = tmp_path / "script-MyScript.yml"
    with path.open("w") as f:
        yaml.dump({"name": "MyScript", IS_CONTENT_PRIVATE_KEY: True}, f)
    mocker.patch.object(
        IntegrationScriptUnifier, "unify", side_effect=lambda _p, data, *_a, **_k: data
    )
    script = Script.construct(  # type: ignore[call-arg]
        object_id="MyScript",
        name="MyScript",
        path=path,
        marketplaces=[MarketplaceVersions.XSOAR],
        type="python",
        is_unified=False,
    )

    assert IS_CONTENT_PRIVATE_KEY not in script.prepare_for_upload(unify_only=True)


@pytest.mark.parametrize(
    "item_class, unifier, handler, suffix",
    [
        (ListObject, ListUnifier, json, "json"),
        (ParsingRule, RuleUnifier, yaml, "yml"),
        (ModelingRule, RuleUnifier, yaml, "yml"),
    ],
)
def test_unify_only_strips_flag(
    tmp_path: Path, mocker, item_class, unifier, handler, suffix: str
):
    path = tmp_path / f"item.{suffix}"
    with path.open("w") as f:
        handler.dump({"name": "a", IS_CONTENT_PRIVATE_KEY: True}, f)
    mocker.patch.object(unifier, "unify", side_effect=lambda _p, data, *_a, **_k: data)
    item = item_class.construct(  # type: ignore[call-arg]
        object_id="a",
        name="a",
        path=path,
        marketplaces=[MarketplaceVersions.XSOAR],
        is_unified=False,
    )

    assert IS_CONTENT_PRIVATE_KEY not in item.prepare_for_upload(unify_only=True)


@pytest.mark.parametrize("strip_internal", [False, True])
def test_dump_pack_metadata_strips_pack_flag_regardless_of_strip_internal(
    tmp_path: Path, strip_internal: bool
):
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out.json"
    source.write_text(
        json.dumps({"name": "P", "internal": True, IS_CONTENT_PRIVATE_ONLY_KEY: True})
    )

    Pack._dump_pack_metadata(
        MagicMock(),
        source,
        destination,
        MarketplaceVersions.XSOAR,
        strip_internal=strip_internal,
    )

    written = get_json(destination)
    assert IS_CONTENT_PRIVATE_ONLY_KEY not in written
    assert ("internal" in written) is (not strip_internal)


def test_dump_metadata_excludes_pack_flag(tmp_path: Path):
    destination = tmp_path / "metadata.json"

    _build_pack(tmp_path).dump_metadata(destination, MarketplaceVersions.XSOAR)

    assert IS_CONTENT_PRIVATE_ONLY_KEY not in destination.read_text()


def test_pack_dump_leaves_no_flag_in_output(tmp_path: Path):
    pack_dir = tmp_path / "Packs" / "TestPack"
    classifier_path = pack_dir / "Classifiers" / "classifier-MyClassifier.json"
    classifier_path.parent.mkdir(parents=True)
    (pack_dir / "README.md").write_text("readme")
    (pack_dir / "pack_metadata.json").write_text(
        json.dumps({"name": "TestPack", IS_CONTENT_PRIVATE_ONLY_KEY: True})
    )
    classifier_path.write_text(
        json.dumps({"id": "MyClassifier", IS_CONTENT_PRIVATE_KEY: True})
    )
    pack = _build_pack(pack_dir)
    pack.content_items.classifier.append(_build_classifier(classifier_path))
    output = tmp_path / "out"

    pack.dump(output, MarketplaceVersions.XSOAR)

    files = [f for f in output.rglob("*") if f.is_file()]
    assert len(files) >= 2
    for file in files:
        text = file.read_text(errors="ignore")
        assert IS_CONTENT_PRIVATE_KEY not in text
        assert IS_CONTENT_PRIVATE_ONLY_KEY not in text
