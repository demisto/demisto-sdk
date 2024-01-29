
import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.commands.get_dependencies import (
    get_dependencies_by_pack_path,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    Direction,
)
from TestSuite.repo import Repo


def create_mini_content(graph_repo: Repo):
    """Creates a content repo with 5 packs dependencies

      +-----+               +-----+               +-----+              +-----+              +------------+
      |Pack1|-------------->|Pack2|-------------->|Pack3|------------->|Pack4|------------->|Pack5 Hidden|
      +-----+  DEPENDS_ON   +-----+  DEPENDS_ON   +-----+  DEPENDS_ON  +-----+  DEPENDS_ON  +------------+
        ^ |   (mandatorily)    ^    (optionally)     ^    (optionally)   | |  (mandatorily)
        | |                    |                     |                   | |
        |  ------------------------------------------                    | |
        |       DEPENDS_ON     |                                         | |
        |      (optionally)     ------------------------------------------ |     DEPENDS_ON
        |                                     DEPENDS_ON                   | (mandatorily, is_test)
        |                                    (mandatorily)                 |
         ------------------------------------------------------------------
    
    Args:
        graph_repo (Repo): the content repo to work with.
    """
    pack1 = graph_repo.create_pack("SamplePack1")
    pack1.set_data(
        dependencies={
            "SamplePack2": {"mandatory": True, "display_name": "SamplePack2"},
            "SamplePack3": {"mandatory": False, "display_name": "SamplePack3"}
        }
    )
    graph_repo.create_pack("SamplePack2").set_data(
        dependencies={
            "SamplePack3": {"mandatory": False, "display_name": "SamplePack3"}
        }
    )
    graph_repo.create_pack("SamplePack3").set_data(
        dependencies={
            "SamplePack4": {"mandatory": False, "display_name": "SamplePack4"}
        }
    )
    pack4 = graph_repo.create_pack("SamplePack4")
    pack4.set_data(
        dependencies={
            "SamplePack2": {"mandatory": True, "display_name": "SamplePack2"},
            "SamplePack5": {"mandatory": True, "display_name": "SamplePack5"}
        }
    )
    graph_repo.create_pack("SamplePack5").set_data(
        hidden=True
    )

    pack1.create_script("SampleScript")

    pack4_test_playbook = pack4.create_test_playbook("SampleTestPlaybook")
    pack4_test_playbook.add_default_task("SampleScript")


def compare(
    result: list,
    expected_list: list,
    dependency_pack: str,
    mandatory_only: bool,
    include_tests: bool,
    show_reasons: bool
) -> None:
    assert len(result) == len(expected_list)
    result.sort(key=lambda r: r["object_id"])
    expected_list.sort(key=lambda r: r["object_id"])
    for actual, expected in zip(result, expected_list):
        assert actual.get("mandatorily") == expected.get("mandatorily")
        assert actual.get("paths")[0].get("is_test") == expected.get("is_test")
        assert actual.get("minDepth") == expected.get("minDepth")

        if mandatory_only:
            assert actual.get("mandatorily")

        if not include_tests:
            assert not any([path.get("is_test") for path in actual.get("paths")])

        if dependency_pack:
            assert actual.get("object_id") == dependency_pack

        if show_reasons:
            assert actual.get("reasons") == expected.get("reasons")
        else:
            assert "reasons" not in actual
        


class TestGetRelationships:
    @pytest.mark.parametrize(
        "pack_id, show_reasons, dependency_pack, all_level_dependencies, marketplace, direction, mandatory_only, include_tests, include_hidden, expected_sources, expected_targets",
        [
            pytest.param(
                "SamplePack2",
                False,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.SOURCES,
                False,
                False,
                False,
                [
                    {
                        "object_id": "SamplePack1",
                        # "paths_count": 1,
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    },
                    {
                        "object_id": "SamplePack4",
                        # "paths_count": 1,
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                [],
                id="Verify source first level dependency",
            ),
            pytest.param(
                "SamplePack2",
                False,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.TARGETS,
                False,
                False,
                False,
                [],
                [
                    {
                        "object_id": "SamplePack3",
                        "mandatorily": False,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                id="Verify target first level dependency",
            ),
            pytest.param(
                "SamplePack4",
                False,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                False,
                [
                    {
                        "object_id": "SamplePack3",
                        "paths_count": 1,
                        "mandatorily": False,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                [
                    {
                        "object_id": "SamplePack1",
                        # "paths_count": 1,
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                id="Verify both directions first level dependencies",
            ),
            pytest.param(
                "SamplePack4",
                False,
                None,
                True,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                False,
                [
                    {
                        "object_id": "SamplePack1",
                        "mandatorily": False,
                        "minDepth": 2,
                        "is_test": False
                    },
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": False,
                        "minDepth": 2,
                        "is_test": False
                    },
                    {
                        "object_id": "SamplePack3",
                        "mandatorily": False,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                [
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    },
                    {
                        "object_id": "SamplePack3",
                        "mandatorily": False,
                        "minDepth": 2,
                        "is_test": False
                    }
                ],
                id="Verify both directions all level dependencies",
            ),
            pytest.param(
                "SamplePack4",
                False,
                None,
                True,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                True,
                False,
                False,
                [],
                [
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                id="Verify both directions all level dependencies, mandatory only",
            ),
            pytest.param(
                "SamplePack4",
                False,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                True,
                False,
                [
                    {
                        "object_id": "SamplePack3",
                        "mandatorily": False,
                        "minDepth": 1,
                        "is_test": False
                    }
                ],
                [
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False
                    },
                    {
                        "object_id": "SamplePack1",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": True,
                    }
                ],
                id="Verify both directions first level dependencies, mandatory only, including tests dependencies",
            ),
            pytest.param(
                "SamplePack4",
                True,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                True,
                False,
                [
                    {
                        "object_id": "SamplePack3",
                        "mandatorily": False,
                        "minDepth": 1,
                        "is_test": False,
                        "reasons": ""
                    }
                ],
                [
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False,
                        "reasons": ""
                    },
                    {
                        "object_id": "SamplePack1",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": True,
                        "reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n"
                    }
                ],
                id="Verify both directions first level dependencies, show reasons, including tests dependencies",
            ),
            pytest.param(
                "SamplePack4",
                False,
                None,
                False,
                MarketplaceVersions.XSOAR,
                Direction.TARGETS,
                False,
                True,
                True,
                [],
                [
                    {
                        "object_id": "SamplePack2",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False,
                    },
                    {
                        "object_id": "SamplePack1",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": True,
                    },
                    {
                        "object_id": "SamplePack5",
                        "mandatorily": True,
                        "minDepth": 1,
                        "is_test": False,
                    }
                ],
                id="Verify target directions, first level, including tests, including hidden",
            )
        ],
    )
    def test_get_dependencies(
        self,
        graph_repo: Repo,
        pack_id: str,
        show_reasons: bool,
        dependency_pack: str,
        all_level_dependencies: bool,
        marketplace: MarketplaceVersions,
        direction: Direction,
        mandatory_only: bool,
        include_tests: bool,
        include_hidden: bool,
        expected_sources: list,
        expected_targets: list,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() for the above test cases.
        Then:
            - Make sure the resulted sources and targets are as expected.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()
        result = get_dependencies_by_pack_path(
            graph,
            pack_id,
            show_reasons,
            dependency_pack,
            all_level_dependencies,
            marketplace,
            direction,
            mandatory_only,
            include_tests,
            False,
            include_hidden,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(sources, expected_sources, dependency_pack, mandatory_only, include_tests, show_reasons)
        compare(targets, expected_targets, dependency_pack, mandatory_only, include_tests, show_reasons)
