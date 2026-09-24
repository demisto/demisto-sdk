"""Tests for region-partitioned duplicate IDs in the pack metadata content items.

The same content item ID may legitimately be reused for variants targeting
different regions, expressed through disjoint ``supportedFeatures``. Such
variants must all be listed in ``metadata.json``, rather than one silently
overriding the other.

Overlap on a feature name means the variants can be active together, so the
pre-existing collapse (and its ``toversion`` tie-breaker) still applies. GR105
is what fails the build for genuinely colliding IDs; this module only covers
what the metadata writer emits.
"""

from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.content_graph.objects.script import Script

AUTOMATION = ContentType.SCRIPT.metadata_name


def _build_script(
    *,
    object_id: str = "VMwareESXiTest",
    name: str = "VMwareESXiTest",
    supported_features=None,
    toversion: str = "99.99.99",
) -> Script:
    """Builds a Script via ``construct()`` (bypassing pydantic validation) so
    its ``summary()`` can be exercised without spinning up the content graph."""
    return Script.construct(  # type: ignore[call-arg]
        object_id=object_id,
        name=name,
        description="VMware ESXi test script.",
        path=Path(f"/tmp/{name}.yml"),
        fromversion="0.0.0",
        toversion=toversion,
        deprecated=False,
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
        supportedModules=None,
        supportedFeatures=supported_features,
    )


def _collect(*scripts: Script) -> dict:
    """Runs the scripts through the metadata collector, in order."""
    metadata = PackMetadata.construct()  # type: ignore[call-arg]
    collected: dict = {}
    for script in scripts:
        metadata._add_item_to_metadata_list(
            collected_content_items=collected,
            content_item=script,
            marketplace=MarketplaceVersions.XSOAR,
        )
    return collected


def test_same_id_disjoint_supported_features_are_both_collected():
    """
    Given:
        - Two scripts sharing the ID ``VMwareESXiTest``, one declaring
          ``supportedFeatures: [harness_v1]`` and the other ``[harness_v2]``,
          with identical from/to versions.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - Both are listed, each retaining its own ``supportedFeatures``, since
          disjoint features mean the two are never active together.
    """
    collected = _collect(
        _build_script(supported_features=["harness_v1"]),
        _build_script(supported_features=["harness_v2"]),
    )

    assert [item["supportedFeatures"] for item in collected[AUTOMATION]] == [
        ["harness_v1"],
        ["harness_v2"],
    ]
    assert {item["id"] for item in collected[AUTOMATION]} == {"VMwareESXiTest"}


def test_same_id_overlapping_supported_features_collapse_to_one():
    """
    Given:
        - Two scripts sharing an ID, both declaring the feature ``Moshe``
          alongside a feature unique to each.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - Only one entry is listed. A shared feature means they can be active
          together, so they are treated as the same item, as before.
    """
    collected = _collect(
        _build_script(supported_features=["Moshe", "a"]),
        _build_script(supported_features=["Moshe", "b"]),
    )

    assert len(collected[AUTOMATION]) == 1
    assert collected[AUTOMATION][0]["supportedFeatures"] == ["Moshe", "a"]


def test_same_id_collapses_when_one_item_declares_no_supported_features():
    """
    Given:
        - Two scripts sharing an ID, where only one declares
          ``supportedFeatures``.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - Only one entry is listed. An absent value means "supported
          everywhere", so non-overlap cannot be proven and the conservative
          collapse is kept.
    """
    collected = _collect(
        _build_script(supported_features=None),
        _build_script(supported_features=["harness_v2"]),
    )

    assert len(collected[AUTOMATION]) == 1


def test_same_id_collapses_when_supported_features_is_empty():
    """
    Given:
        - Two scripts sharing an ID, where one declares an empty
          ``supportedFeatures`` list.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - Only one entry is listed. An empty list carries no restriction, so it
          is treated like an absent value rather than as disjoint.
    """
    collected = _collect(
        _build_script(supported_features=[]),
        _build_script(supported_features=["harness_v2"]),
    )

    assert len(collected[AUTOMATION]) == 1


def test_higher_toversion_still_replaces_within_the_same_feature_partition():
    """
    Given:
        - Two scripts sharing an ID and a feature, the second having a higher
          ``toversion``.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - The entry is replaced by the higher-``toversion`` one, proving the
          pre-existing version tie-breaker still applies within a partition.
    """
    collected = _collect(
        _build_script(supported_features=["harness_v1"], toversion="6.0.0"),
        _build_script(supported_features=["harness_v1"], toversion="8.0.0"),
    )

    assert len(collected[AUTOMATION]) == 1
    assert collected[AUTOMATION][0]["toversion"] == "8.0.0"


def test_distinct_ids_are_unaffected():
    """
    Given:
        - Two scripts with different IDs and no ``supportedFeatures``.
    When:
        - Both are added to the pack metadata content items list.
    Then:
        - Both are listed, as they were before the feature-aware change.
    """
    collected = _collect(
        _build_script(object_id="ScriptA", name="ScriptA"),
        _build_script(object_id="ScriptB", name="ScriptB"),
    )

    assert {item["id"] for item in collected[AUTOMATION]} == {"ScriptA", "ScriptB"}
