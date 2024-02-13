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
            "SamplePack3": {"mandatory": False, "display_name": "SamplePack3"},
        }
    )
    pack2 = graph_repo.create_pack("SamplePack2")
    pack2.set_data(
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
            "SamplePack5": {"mandatory": True, "display_name": "SamplePack5"},
        }
    )
    graph_repo.create_pack("SamplePack5").set_data(hidden=True)

    pack2.create_script("SampleScript2")
    pack2.create_integration("SampleIntegration2").set_commands(["pack2-test-command"])
    pack1.create_script("SampleScript").yml.update(
        {"dependson": {"must": ["SampleScript2", "pack2-test-command"]}}
    )

    pack4_test_playbook = pack4.create_test_playbook("SampleTestPlaybook")
    pack4_test_playbook.add_default_task("SampleScript")


def compare(
    result: list,
    expected_list: list,
    dependency_pack: str = "",
    mandatory_only: bool = False,
    include_tests: bool = False,
    show_reasons: bool = False,
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
            assert actual.get("formatted_reasons") == expected.get("formatted_reasons")
        else:
            assert "reasons" not in actual
            assert "formatted_reasons" not in actual


class TestGetDependencies:
    def test_get_dependencies_only_sources(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get only source dependents.
        Then:
            - Make sure the resulted sources and target dependencies are as expected.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack1",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {
                    "Script:SampleScript": [
                        "Integration:SampleIntegration2",
                        "Script:SampleScript2",
                    ]
                },
                "formatted_reasons": "* Script:SampleScript -> [USES]:\n  - Integration:SampleIntegration2\n  - Script:SampleScript2\n",
            },
            {
                "object_id": "SamplePack4",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {},
                "formatted_reasons": "",
            },
        ]
        expected_targets = []

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack2",
            show_reasons=True,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.SOURCES,
            mandatory_only=False,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            show_reasons=True,
        )

    def test_get_dependencies_only_targets(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get only target dependencies.
        Then:
            - Make sure the resulted sources and target dependencies are as expected.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = []
        expected_targets = [
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
            }
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack2",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.TARGETS,
            mandatory_only=False,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
        )
        compare(
            targets,
            expected_targets,
        )

    def test_get_dependencies_both_directions(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both directions dependencies.
        Then:
            - Make sure the resulted sources and target dependencies are as expected.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack3",
                "paths_count": 1,
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
            }
        ]
        expected_targets = [
            {
                "object_id": "SamplePack1",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
            }
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
        )
        compare(
            targets,
            expected_targets,
        )

    def test_get_dependencies_both_dirs_all_level(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both directions, and all level dependencies.
        Then:
            - Make sure the resulted sources and targets are as expected.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack1",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
            },
            {
                "object_id": "SamplePack2",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
            },
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
            },
        ]
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
            },
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
        )
        compare(
            targets,
            expected_targets,
        )

    def test_get_dependencies_both_dirs_mandatory_all_level(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get only mandatory, both directions, all level dependencies.
        Then:
            - Make sure the resulted sources and targets are as expected and are only mandatory dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = []
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
            }
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=True,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            mandatory_only=True,
        )
        compare(
            targets,
            expected_targets,
            mandatory_only=True,
        )

    def test_get_dependencies_include_tests(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both directions, first level, including test dependencies.
        Then:
            - Make sure the resulted sources and targets are as expected and are including test dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
            }
        ]
        expected_targets = [
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
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=True,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            include_tests=True,
        )
        compare(
            targets,
            expected_targets,
            include_tests=True,
        )

    def test_get_dependencies_include_tests_and_hidden(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get only target, first level deps, including tests deps and hidden packs.
        Then:
            - Make sure the resulted sources and targets are as expected and are including test and hidden packs dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = []
        expected_targets = [
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
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=False,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.TARGETS,
            mandatory_only=False,
            include_tests=True,
            include_deprecated=False,
            include_hidden=True,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            include_tests=True,
            show_reasons=True,
        )

    def test_get_dependencies_include_tests_and_reasons(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get target first level dependencies, including test deps, and show reasons.
        Then:
            - Make sure the resulted sources and targets are as expected and are including test and hidden packs dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = []
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {},
                "formatted_reasons": "",
            },
            {
                "object_id": "SamplePack1",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": True,
                "reasons": {"TestPlaybook:SamplePlaybookTest": ["Script:SampleScript"]},
                "formatted_reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n",
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack4",
            show_reasons=True,
            dependency_pack="",
            all_level_dependencies=False,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.TARGETS,
            mandatory_only=False,
            include_tests=True,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            include_tests=True,
            show_reasons=True,
        )

    def test_get_dependencies_both_dirs_all_level_reasons(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both dirs, all level deps, and show reasons.
        Then:
            - Make sure the resulted sources and targets are as expected including the reasons.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = []
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {
                    "Script:SampleScript": [
                        "Integration:SampleIntegration2",
                        "Script:SampleScript2",
                    ]
                },
                "formatted_reasons": "* Script:SampleScript -> [USES]:\n  - Integration:SampleIntegration2\n  - Script:SampleScript2\n",
            },
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
                "reasons": {},
                "formatted_reasons": "",
            },
            {
                "object_id": "SamplePack4",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
                "reasons": [
                    ["SamplePack1", "SamplePack3", "SamplePack4"],
                    [
                        "SamplePack1",
                        "SamplePack2",
                        "SamplePack3",
                        "SamplePack4",
                    ],
                ],
                "formatted_reasons": "* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4\n* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack2 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4",
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack1",
            show_reasons=True,
            dependency_pack="",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=False,
            include_deprecated=False,
            include_hidden=False,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            show_reasons=True,
        )

    def test_get_dependencies_both_dirs_all_level_reasons_tests_hidden(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both dirs, all level deps, show reasons, including test deps and hidden packs.
        Then:
            - Make sure the resulted sources and targets are as expected and are including reasons, test and hidden packs dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack2",
                "mandatorily": False,
                "minDepth": 3,
                "is_test": True,
                "reasons": [
                    ["SamplePack2", "SamplePack3", "SamplePack4", "SamplePack1"]
                ],
                "formatted_reasons": "* Pack:SamplePack2 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4 -> [DEPENDS_ON] -> Pack:SamplePack1",
            },
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": True,
                "reasons": [["SamplePack3", "SamplePack4", "SamplePack1"]],
                "formatted_reasons": "* Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4 -> [DEPENDS_ON] -> Pack:SamplePack1",
            },
            {
                "object_id": "SamplePack4",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": True,
                "reasons": {"TestPlaybook:SamplePlaybookTest": ["Script:SampleScript"]},
                "formatted_reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n",
            },
        ]
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {
                    "Script:SampleScript": [
                        "Integration:SampleIntegration2",
                        "Script:SampleScript2",
                    ]
                },
                "formatted_reasons": "* Script:SampleScript -> [USES]:\n  - Integration:SampleIntegration2\n  - Script:SampleScript2\n",
            },
            {
                "object_id": "SamplePack3",
                "mandatorily": False,
                "minDepth": 1,
                "is_test": False,
                "reasons": {},
                "formatted_reasons": "",
            },
            {
                "object_id": "SamplePack4",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
                "reasons": [
                    ["SamplePack1", "SamplePack3", "SamplePack4"],
                    [
                        "SamplePack1",
                        "SamplePack2",
                        "SamplePack3",
                        "SamplePack4",
                    ],
                ],
                "formatted_reasons": "* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4\n* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack2 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4",
            },
            {
                "object_id": "SamplePack5",
                "mandatorily": False,
                "minDepth": 3,
                "is_test": False,
                "reasons": [
                    [
                        "SamplePack1",
                        "SamplePack3",
                        "SamplePack4",
                        "SamplePack5",
                    ],
                    [
                        "SamplePack1",
                        "SamplePack2",
                        "SamplePack3",
                        "SamplePack4",
                        "SamplePack5",
                    ],
                ],
                "formatted_reasons": "* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4 -> [DEPENDS_ON] -> Pack:SamplePack5\n* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack2 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4 -> [DEPENDS_ON] -> Pack:SamplePack5",
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack1",
            show_reasons=True,
            dependency_pack="",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=True,
            include_deprecated=False,
            include_hidden=True,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            include_tests=True,
            show_reasons=True,
        )

    def test_get_dependencies_all_level_mandatory_tests_hidden(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get both dirs, only mandatory, all level deps, show reasons, including test deps and hidden packs.
        Then:
            - Make sure the resulted sources and targets are only mandatory as expected and are including reasons, test and hidden packs dependencies.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack4",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": True,
                "reasons": {"TestPlaybook:SamplePlaybookTest": ["Script:SampleScript"]},
                "formatted_reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n",
            },
        ]
        expected_targets = [
            {
                "object_id": "SamplePack2",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": False,
                "reasons": {
                    "Script:SampleScript": [
                        "Integration:SampleIntegration2",
                        "Script:SampleScript2",
                    ]
                },
                "formatted_reasons": "* Script:SampleScript -> [USES]:\n  - Integration:SampleIntegration2\n  - Script:SampleScript2\n",
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack1",
            show_reasons=True,
            dependency_pack="",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=True,
            include_tests=True,
            include_deprecated=False,
            include_hidden=True,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            mandatory_only=True,
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            mandatory_only=True,
            include_tests=True,
            show_reasons=True,
        )

    def test_get_dependencies_specific_dependency_all_level(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get the result for a specific dependency "SamplePack4".
        Then:
            - Make sure the returned result is only for the given dependency pack ID.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack4",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": True,
                "reasons": {"TestPlaybook:SamplePlaybookTest": ["Script:SampleScript"]},
                "formatted_reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n",
            },
        ]
        expected_targets = [
            {
                "object_id": "SamplePack4",
                "mandatorily": False,
                "minDepth": 2,
                "is_test": False,
                "reasons": [
                    ["SamplePack1", "SamplePack3", "SamplePack4"],
                    [
                        "SamplePack1",
                        "SamplePack2",
                        "SamplePack3",
                        "SamplePack4",
                    ],
                ],
                "formatted_reasons": "* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4\n* Pack:SamplePack1 -> [DEPENDS_ON] -> Pack:SamplePack2 -> [DEPENDS_ON] -> Pack:SamplePack3 -> [DEPENDS_ON] -> Pack:SamplePack4",
            },
        ]

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack1",
            show_reasons=True,
            dependency_pack="SamplePack4",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=False,
            include_tests=True,
            include_deprecated=False,
            include_hidden=True,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            dependency_pack="SamplePack4",
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            dependency_pack="SamplePack4",
            include_tests=True,
            show_reasons=True,
        )

    def test_get_dependencies_specific_dependency_mandatory(
        self,
        graph_repo: Repo,
    ) -> None:
        """
        Given:
            - A repository with multiple packs and dependencies.
        When:
            - Running get_dependencies_by_pack_path() to get the result for a specific dependency "SamplePack4", only mandatory.
        Then:
            - Make sure the returned result is only for the given dependency pack ID, and only mandatory.
        """
        create_mini_content(graph_repo)
        graph = graph_repo.create_graph()

        expected_sources = [
            {
                "object_id": "SamplePack4",
                "mandatorily": True,
                "minDepth": 1,
                "is_test": True,
                "reasons": {"TestPlaybook:SamplePlaybookTest": ["Script:SampleScript"]},
                "formatted_reasons": "* TestPlaybook:SamplePlaybookTest -> [USES] -> Script:SampleScript\n",
            },
        ]
        expected_targets = []

        result = get_dependencies_by_pack_path(
            graph,
            pack_id="SamplePack1",
            show_reasons=True,
            dependency_pack="SamplePack4",
            all_level_dependencies=True,
            marketplace=MarketplaceVersions.XSOAR,
            direction=Direction.BOTH,
            mandatory_only=True,
            include_tests=True,
            include_deprecated=False,
            include_hidden=True,
        )
        sources, targets = result["source_dependents"], result["target_dependencies"]
        compare(
            sources,
            expected_sources,
            dependency_pack="SamplePack4",
            mandatory_only=True,
            include_tests=True,
            show_reasons=True,
        )
        compare(
            targets,
            expected_targets,
            dependency_pack="SamplePack4",
            mandatory_only=True,
            include_tests=True,
            show_reasons=True,
        )
