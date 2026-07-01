"""Tests verifying that `internal: true` is stripped from script YAMLs and
pack metadata files **only** during the ``demisto-sdk upload`` flow (i.e. when
``strip_internal=True`` is passed), so the uploaded content is visible to the
user. Other flows (``prepare-content``, artifact builds) must keep the field
intact."""

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
    """Build a Script instance via ``construct()`` (bypasses pydantic
    validation) so we can call its methods without spinning up the content
    graph."""
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
# Script YAML  -- BaseScript.prepare_for_upload should strip `internal` only
# when ``strip_internal=True`` is passed (the upload flow). Other callers
# (prepare-content, artifact builds) pass no flag / False and the field must
# be preserved.
# ---------------------------------------------------------------------------


def test_base_script_prepare_for_upload_strips_internal_when_flag_true(mocker):
    """
    Given:
        - A Script whose underlying upload data contains ``internal: true``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked with
          ``strip_internal=True`` (i.e. the upload flow).
    Then:
        - The ``internal`` key is removed from the resulting data so the
          uploaded script is visible to the user.
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
    prepared = script.prepare_for_upload(strip_internal=True)

    assert "internal" not in prepared
    assert prepared["name"] == "MyScript"
    assert prepared["type"] == "python"


def test_base_script_prepare_for_upload_keeps_internal_when_flag_false(mocker):
    """
    Given:
        - A Script whose underlying upload data contains ``internal: true``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked **without**
          ``strip_internal`` (i.e. the prepare-content / artifact-build flow).
    Then:
        - The ``internal`` key is preserved on the resulting data, because
          the strip is scoped to the upload flow only.
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
    prepared = script.prepare_for_upload()  # no strip_internal -> defaults to False

    assert prepared.get("internal") is True
    assert prepared["name"] == "MyScript"


def test_base_script_prepare_for_upload_no_internal_field(mocker):
    """
    Given:
        - A Script whose underlying upload data does not contain ``internal``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked with
          ``strip_internal=True``.
    Then:
        - The data is returned unchanged (no ``KeyError``, no ``internal``
          added).
    """
    base_data = {"name": "MyScript", "script": "-", "type": "python"}
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload(strip_internal=True)

    assert "internal" not in prepared
    assert prepared == base_data


def test_base_script_prepare_for_upload_internal_false_is_stripped(mocker):
    """
    Given:
        - A Script whose underlying upload data contains ``internal: false``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked with
          ``strip_internal=True``.
    Then:
        - The ``internal`` key is removed from the resulting data; the
          upload-flow strip is unconditional regardless of value.
    """
    base_data = {"name": "MyScript", "internal": False}
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload(strip_internal=True)

    assert "internal" not in prepared


def test_base_script_prepare_for_upload_strips_isInternal_when_flag_true(mocker):
    """
    Given:
        - A Script whose underlying upload data contains ``isInternal: true``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked with
          ``strip_internal=True`` (i.e. the upload flow).
    Then:
        - The ``isInternal`` key is removed from the resulting data so the
          uploaded script is listed in the pack metadata.
        - The other keys are preserved unchanged.
    """
    base_data = {
        "name": "MyScript",
        "script": "-",
        "type": "python",
        "isInternal": True,
    }
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload(strip_internal=True)

    assert "isInternal" not in prepared
    assert prepared["name"] == "MyScript"
    assert prepared["type"] == "python"


def test_base_script_prepare_for_upload_keeps_isInternal_when_flag_false(mocker):
    """
    Given:
        - A Script whose underlying upload data contains ``isInternal: true``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked **without**
          ``strip_internal`` (i.e. the prepare-content / artifact-build flow).
    Then:
        - The ``isInternal`` key is preserved on the resulting data, because
          the strip is scoped to the upload flow only.
    """
    base_data = {
        "name": "MyScript",
        "script": "-",
        "type": "python",
        "isInternal": True,
    }
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload()  # no strip_internal -> defaults to False

    assert prepared.get("isInternal") is True
    assert prepared["name"] == "MyScript"


def test_base_script_prepare_for_upload_strips_both_internal_fields(mocker):
    """
    Given:
        - A Script whose underlying upload data contains both ``internal: true``
          and ``isInternal: true``.
    When:
        - ``BaseScript.prepare_for_upload`` is invoked with
          ``strip_internal=True``.
    Then:
        - Both ``internal`` and ``isInternal`` keys are removed from the
          resulting data.
    """
    base_data = {
        "name": "MyScript",
        "script": "-",
        "type": "python",
        "internal": True,
        "isInternal": True,
    }
    mocker.patch.object(
        IntegrationScript,
        "prepare_for_upload",
        return_value=dict(base_data),
    )
    mocker.patch.object(BaseScript, "get_supported_native_images", return_value=[])

    script = _build_minimal_script()
    prepared = script.prepare_for_upload(strip_internal=True)

    assert "internal" not in prepared
    assert "isInternal" not in prepared


# ---------------------------------------------------------------------------
# should_ignore_item_in_metadata -- the upload flow (strip_internal=True)
# must NOT skip scripts marked ``isInternal: true``, so they appear in the
# generated metadata.json's content items list. Other flows must continue
# skipping them as before (preserving PR #5025 semantics).
# ---------------------------------------------------------------------------


def test_should_ignore_item_in_metadata_skips_internal_script_by_default():
    """
    Given:
        - A Script content item with ``is_internal=True``.
    When:
        - ``should_ignore_item_in_metadata`` is called without the
          ``strip_internal`` flag (the prepare-content / artifact-build flow).
    Then:
        - The function returns True, preserving the PR #5025 behavior of
          excluding internal scripts from the pack metadata content items.
    """
    from demisto_sdk.commands.content_graph.common import ContentType
    from demisto_sdk.commands.content_graph.objects.pack_metadata import (
        should_ignore_item_in_metadata,
    )

    content_item = MagicMock()
    content_item.is_test = False
    content_item.is_silent = False
    content_item.is_llm = False
    content_item.is_internal = True
    content_item.marketplaces = [MarketplaceVersions.XSOAR]
    content_item.content_type = ContentType.SCRIPT
    content_item.name = "MyInternalScript"

    assert (
        should_ignore_item_in_metadata(content_item, MarketplaceVersions.XSOAR) is True
    )


def test_should_ignore_item_in_metadata_keeps_internal_script_on_upload():
    """
    Given:
        - A Script content item with ``is_internal=True``.
    When:
        - ``should_ignore_item_in_metadata`` is called with
          ``strip_internal=True`` (the upload flow).
    Then:
        - The function returns False so the internal script is included in
          the generated ``metadata.json`` content items list, matching the
          fact that the script's ``isInternal`` field is also stripped from
          the dumped YAML on this flow.
    """
    from demisto_sdk.commands.content_graph.common import ContentType
    from demisto_sdk.commands.content_graph.objects.pack_metadata import (
        should_ignore_item_in_metadata,
    )

    content_item = MagicMock()
    content_item.is_test = False
    content_item.is_silent = False
    content_item.is_llm = False
    content_item.is_internal = True
    content_item.marketplaces = [MarketplaceVersions.XSOAR]
    content_item.content_type = ContentType.SCRIPT
    content_item.name = "MyInternalScript"

    assert (
        should_ignore_item_in_metadata(
            content_item,
            MarketplaceVersions.XSOAR,
            strip_internal=True,
        )
        is False
    )


def test_should_ignore_item_in_metadata_still_skips_test_on_upload_flow():
    """
    Given:
        - A test Script content item.
    When:
        - ``should_ignore_item_in_metadata`` is called with ``strip_internal=True``.
    Then:
        - The function still returns True - ``strip_internal`` only relaxes
          the ``isInternal`` skip rule, not the unrelated ``is_test`` rule.
    """
    from demisto_sdk.commands.content_graph.common import ContentType
    from demisto_sdk.commands.content_graph.objects.pack_metadata import (
        should_ignore_item_in_metadata,
    )

    content_item = MagicMock()
    content_item.is_test = True
    content_item.is_silent = False
    content_item.is_llm = False
    content_item.is_internal = False
    content_item.marketplaces = [MarketplaceVersions.XSOAR]
    content_item.content_type = ContentType.SCRIPT
    content_item.name = "MyTestScript"

    assert (
        should_ignore_item_in_metadata(
            content_item,
            MarketplaceVersions.XSOAR,
            strip_internal=True,
        )
        is True
    )


# ---------------------------------------------------------------------------
# pack_metadata.json (the file copied verbatim from disk during dump).
# ---------------------------------------------------------------------------


def _call_dump_pack_metadata(
    source: Path, destination: Path, strip_internal: bool = False
) -> None:
    """Invoke ``Pack._dump_pack_metadata`` as an unbound method, passing a
    stub ``self`` so we don't have to instantiate a real (graph-backed)
    ``Pack``."""
    fake_self = MagicMock()
    Pack._dump_pack_metadata(
        fake_self,
        source,
        destination,
        MarketplaceVersions.XSOAR,
        strip_internal=strip_internal,
    )


def test_dump_pack_metadata_strips_internal_when_flag_true(tmp_path):
    """
    Given:
        - A ``pack_metadata.json`` containing ``"internal": true``.
    When:
        - ``Pack._dump_pack_metadata`` is called with ``strip_internal=True``.
    Then:
        - The destination ``pack_metadata.json`` no longer contains
          ``internal``.
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

    _call_dump_pack_metadata(source, destination, strip_internal=True)

    written = get_json(destination)
    assert "internal" not in written
    assert written["name"] == "TestPack"
    assert written["currentVersion"] == "1.0.0"


def test_dump_pack_metadata_keeps_internal_when_flag_false(tmp_path):
    """
    Given:
        - A ``pack_metadata.json`` containing ``"internal": true``.
    When:
        - ``Pack._dump_pack_metadata`` is called **without**
          ``strip_internal`` (the default for prepare-content / artifact
          builds).
    Then:
        - The destination ``pack_metadata.json`` preserves the ``internal``
          field (it is only resolved for managed/source suffixes, which are
          absent here, so the content is unchanged).
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    metadata: Dict[str, Any] = {
        "name": "TestPack",
        "internal": True,
        "currentVersion": "1.0.0",
    }
    source.write_text(json.dumps(metadata))

    _call_dump_pack_metadata(source, destination)  # strip_internal=False (default)

    # Content is preserved (no managed/source suffixes to resolve).
    written = get_json(destination)
    assert written == metadata
    assert written.get("internal") is True


def test_dump_pack_metadata_no_internal_field(tmp_path):
    """
    Given:
        - A ``pack_metadata.json`` that does not contain the ``internal``
          key.
    When:
        - ``Pack._dump_pack_metadata`` is called with ``strip_internal=True``.
    Then:
        - The destination contains the same data (round-tripped through
          JSON).
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    metadata = {"name": "TestPack", "currentVersion": "1.0.0"}
    source.write_text(json.dumps(metadata))

    _call_dump_pack_metadata(source, destination, strip_internal=True)

    written = get_json(destination)
    assert "internal" not in written
    assert written == metadata


def test_dump_pack_metadata_falls_back_to_copy_on_invalid_json(tmp_path):
    """
    Given:
        - A ``pack_metadata.json`` that cannot be parsed as JSON.
    When:
        - ``Pack._dump_pack_metadata`` is called with ``strip_internal=True``.
    Then:
        - The original file is copied as-is to the destination (no crash).
    """
    source = tmp_path / "pack_metadata.json"
    destination = tmp_path / "out" / "pack_metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    raw = "this is not valid json"
    source.write_text(raw)

    _call_dump_pack_metadata(source, destination, strip_internal=True)

    assert destination.read_text() == raw


# ---------------------------------------------------------------------------
# metadata.json (generated by Pack.dump_metadata).
# ---------------------------------------------------------------------------


def test_dump_metadata_excludes_internal_field_when_flag_true():
    """
    Given:
        - The ``Pack.dump_metadata`` source.
    When:
        - Inspecting the function source.
    Then:
        - It includes a code path that adds ``"internal"`` to the
          ``excluded_fields_from_metadata`` set when ``strip_internal`` is
          true, so the upload flow will exclude it from the generated
          ``metadata.json``.
    """
    import inspect

    source = inspect.getsource(Pack.dump_metadata)
    # The conditional must add "internal" to the excluded set.
    assert "strip_internal" in source, (
        "Pack.dump_metadata must gate the `internal` exclusion behind the "
        "`strip_internal` flag so it is only stripped on the upload flow."
    )
    assert '"internal"' in source, (
        "Pack.dump_metadata must (conditionally) exclude the `internal` field "
        "from the dumped metadata.json on the upload flow so the uploaded "
        "pack is visible to users."
    )
