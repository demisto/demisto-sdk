import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.commands.get_dependencies import (
    get_dependencies_by_pack_path,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    Direction,
)
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    repository,  # noqa: F401
    setup_method,  # noqa: F401
)
from demisto_sdk.commands.content_graph.tests.get_relationships_test import (
    compare,
    create_mini_content,
)


class TestGetDependencies:
    @pytest.mark.parametrize(
        "pack_id, all_level_dependencies, marketplace, direction, mandatory_only, include_tests, expected_dependents, expected_dependencies",
        [
            pytest.param(
                "SamplePack3",
                True,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [],
                id="Verify dependencies - don't include tests",
            ),
            pytest.param(
                "SamplePack3",
                True,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                True,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack2",
                        "paths_count": 1,
                        "mandatorily": True,
                    },
                    {
                        "filepath": "Packs/SamplePack",
                        "paths_count": 2,
                        "mandatorily": True,
                    },
                ],
                id="Verify dependencies - include tests",
            ),
        ],
    )
    def test_get_relationships(
        self,
        repository: ContentDTO,  # noqa: F811
        pack_id: str,
        all_level_dependencies: bool,
        marketplace: MarketplaceVersions,
        direction: Direction,
        mandatory_only: bool,
        include_tests: bool,
        expected_dependents: list,
        expected_dependencies: list,
    ) -> None:
        """
        Given:
            - A mocked model of a repository.
        When:
            - Running get_dependencies_by_pack_path() for the above test cases.
        Then:
            - Make sure the resulted dependencies and dependents are as expected.
        """
        create_mini_content(repository)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            result = get_dependencies_by_pack_path(
                interface,
                pack_id=pack_id,
                all_level_dependencies=all_level_dependencies,
                marketplace=marketplace,
                direction=direction,
                mandatory_only=mandatory_only,
                include_tests=include_tests,
                include_deprecated=False,
                include_hidden=False,
            )
            dependents, dependencies = result["dependents"], result["dependencies"]
        compare(dependents, expected_dependents)
        compare(dependencies, expected_dependencies)
