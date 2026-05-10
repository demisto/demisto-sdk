"""Tests verifying that `internal: true` is stripped from script YAMLs and
pack metadata files during the upload preparation, so the uploaded content is
visible to the user."""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.objects.base_script import BaseScript
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.script import Script


def _build_minimal_script() -> Script:
    """Build a Script instance via `construct()` (bypasses pydantic validation)
    so we can call its methods without spinning up the content graph."""
    return Script.construct(  # type: ignore[call-arg]
        object_id="MyScript",
        name="MyScript",
        path=Path("/tmp/MyScript.yml"),
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
    )


# ---------------------------------------------------------------------------
# Script YAML  -- BaseScript.prepare_for_upload should strip `internal`.
# ---------------------------------------------------------------------------


def test_base_script_prepare_for_upload_strips_internal_true(mocker):
    """
    Given:
        - A Script whose underlying upload data contains `internal: true`.
    When:
        - BaseScript.prepare_for_upload is invoked.
    Then:
        - The `internal` key is removed from the resulting data, so the script
          uploaded to the server is visible to the user.
        - The other keys are preserved unchanged.
    """
    base_data = {
        "name": "MyScript",
        "script": "-",
        "type": "python",
        "internal": True,
    }
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload()

    assert "internal" not in prepared
    assert prepared["name"] == "MyScript"
    assert prepared["type"] == "python"


def test_base_script_prepare_for_upload_no_internal_field(mocker):
    """
    Given:
        - A Script whose underlying upload data does not contain `internal`.
    When:
        - BaseScript.prepare_for_upload is invoked.
    Then:
        - The data is returned unchanged (no KeyError, no `internal` added).
    """
    base_data = {"name": "MyScript", "script": "-", "type": "python"}
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload()

    assert "internal" not in prepared
    assert prepared == base_data


def test_base_script_prepare_for_upload_internal_false_is_kept_out(mocker):
    """
    Given:
        - A Script whose underlying upload data contains `internal: false`.
    When:
        - BaseScript.prepare_for_upload is invoked.
    Then:
        - The `internal` key is removed from the resulting data (we always
          strip the field, regardless of value).
    """
    base_data = {"name": "MyScript", "internal": False}
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload()

    assert "internal" not in prepared


# ---------------------------------------------------------------------------
# pack_metadata.json (the file copied verbatim from disk during dump).
# ---------------------------------------------------------------------------


def _call_dump_pack_metadata(source: Path, destination: Path) -> None:
    """Invoke Pack._dump_pack_metadata as an unbound method, passing a stub
    self so we don't have to instantiate a real (graph-backed) Pack."""
    fake_self = MagicMock()
    Pack._dump_pack_metadata(fake_self, source, destination)


def test_dump_pack_metadata_strips_internal_true(tmp_path):
    """
    Given:
        - A pack_metadata.json containing `"internal": true`.
    When:
        - Pack._dump_pack_metadata is called.
    Then:
        - The destination pack_metadata.json no longer contains `internal`.
        - Other fields are preserved unchanged.
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    metadata: Dict[str, Any] = {
        "name": "TestPack",
        "description": "desc",
        "support": "community",
        "internal": True,
        "currentVersion": "1.0.0",
    }
    source.write_text(json.dumps(metadata))

    _call_dump_pack_metadata(source, destination)

    written = get_json(destination)
    assert "internal" not in written
    assert written["name"] == "TestPack"
    assert written["currentVersion"] == "1.0.0"


def test_dump_pack_metadata_no_internal_field(tmp_path):
    """
    Given:
        - A pack_metadata.json that does not contain the `internal` key.
    When:
        - Pack._dump_pack_metadata is called.
    Then:
        - The destination contains the same data (round-tripped through JSON).
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    metadata = {"name": "TestPack", "currentVersion": "1.0.0"}
    source.write_text(json.dumps(metadata))

    _call_dump_pack_metadata(source, destination)

    written = get_json(destination)
    assert "internal" not in written
    assert written == metadata


def test_dump_pack_metadata_falls_back_to_copy_on_invalid_json(tmp_path):
    """
    Given:
        - A pack_metadata.json that cannot be parsed as JSON.
    When:
        - Pack._dump_pack_metadata is called.
    Then:
        - The original file is copied as-is to the destination (no crash).
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    raw = "this is not valid json"
    source.write_text(raw)

    _call_dump_pack_metadata(source, destination)

    assert destination.read_text() == raw


# ---------------------------------------------------------------------------
# metadata.json (generated by Pack.dump_metadata).
# ---------------------------------------------------------------------------


def test_dump_metadata_excludes_internal_field(tmp_path):
    """
    Given:
        - The set of excluded fields used by Pack.dump_metadata.
    When:
        - Inspecting the function source.
    Then:
        - The `internal` field is included in the excluded set, so it will
          never be written to the generated metadata.json.

    This is a lightweight guarantee that future edits don't accidentally drop
    the exclusion. The full end-to-end behavior (graph-backed pack -> dumped
    metadata.json) is exercised by `pack_metadata_graph_test.py`.
    """
    import inspect

    source = inspect.getsource(Pack.dump_metadata)
    # The set literal must include the `internal` key.
    assert '"internal"' in source, (
        "Pack.dump_metadata must exclude the `internal` field from the dumped "
        "metadata.json so that the uploaded pack is visible to users."
    )
