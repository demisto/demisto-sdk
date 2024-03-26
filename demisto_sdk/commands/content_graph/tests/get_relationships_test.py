from pathlib import Path

import pytest
from create_content_graph_test import (
    mock_integration,
    mock_pack,
    mock_script,
    mock_test_playbook,
    repository,  # noqa: F401
)

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    Direction,
    get_relationships_by_path,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO


def create_mini_content(repository: ContentDTO):  # noqa: F811
    """Creates a content repo with three packs and relationships

              +-----+                        +-----+      +-----+
              |Pack1|                        |Pack2|      |Pack3|
              +-----+                        +-----+      +-----+
                 ^                              ^            ^
                 |  IN_PACK             IN_PACK |            |  IN_PACK
             +---------                         |         ---------
             |         |                        |        |         |
             |         |                        |        |         |
          +-----+   +-----+                     |      +-----+   +-----+
      --> |Intg1|   |Scrp1|                     |      |ApiMd|   | TPB | --
     |    +-----+   +-----+                     |      +-----+   +-----+   |
     |    | |  ^       ^                        |         ^       ^   |    |     USES
     |    | |  |       |                        |         |       |   |    | (mandatorily)
     |    | |  |       | USES (mandatorily)  +-----+      |       |   |    |
     |    | |  |        ---------------------|Scrp2|<-----|-------|---|----
     |    | |   ---------------------------- +-----+      |       |   |
     |    | |            USES (optionally)                |       |   |
     |    | |                                             |       |   |
     |    |  ---------------------------------------------        |   |
     |    |                   IMPORTS                             |   |
     |     -------------------------------------------------------    |
     |                        TESTED_BY                               |
      ----------------------------------------------------------------
                            USES (mandatorily)

    Args:
        repository (ContentDTO): the content dto to populate
    """
    pack1 = mock_pack(
        name="SamplePack",
        path=Path("Packs/SamplePack"),
        repository=repository,
    )
    pack2 = mock_pack(
        name="SamplePack2",
        path=Path("Packs/SamplePack2"),
        repository=repository,
    )
    pack3 = mock_pack(
        name="SamplePack3",
        path=Path("Packs/SamplePack3"),
        repository=repository,
    )

    # pack1 content items
    pack1_integration = mock_integration(
        path=Path(
            "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml"
        ),
        pack=pack1,
    )
    pack1_script = mock_script(
        path=Path("Packs/SamplePack/Scripts/SampleScript/SampleScript.yml"),
        pack=pack1,
    )

    # pack2 content items
    pack2_script = mock_script(
        "SampleScript2",
        path=Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
        pack=pack2,
        uses=[(pack1_integration, False), (pack1_script, True)],
    )

    # pack3 content items
    mock_script(
        "TestApiModule",
        path=Path("Packs/SamplePack3/Scripts/TestApiModule/TestApiModule.yml"),
        pack=pack3,
        importing_items=[pack1_integration],
    )
    mock_test_playbook(
        path=Path(
            "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml"
        ),
        pack=pack3,
        uses=[(pack1_integration, True), (pack2_script, True)],
        tested_items=[pack1_integration],
    )


def compare(result: list, expected: list) -> None:
    assert len(result) == len(expected)
    result.sort(key=lambda r: r["filepath"])
    expected.sort(key=lambda r: r["filepath"])
    for actual, expected in zip(result, expected):
        assert actual.get("mandatorily") == expected.get("mandatorily")
        assert len(actual["paths"]) == expected["paths_count"]


class TestGetRelationships:
    @pytest.mark.parametrize(
        "filepath, relationship, content_type, depth, marketplace, direction, mandatory_only, include_tests, expected_sources, expected_targets",
        [
            pytest.param(
                Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [
                    {
                        "filepath": "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                [
                    {
                        "filepath": "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml",
                        "mandatorily": False,
                        "paths_count": 1,
                    },
                    {
                        "filepath": "Packs/SamplePack/Scripts/SampleScript/SampleScript.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships, expecting sources and targets",
            ),
            pytest.param(
                Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.SOURCES,
                False,
                False,
                [
                    {
                        "filepath": "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                [],
                id="Verify USES relationships, sources only",
            ),
            pytest.param(
                Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.TARGETS,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml",
                        "mandatorily": False,
                        "paths_count": 1,
                    },
                    {
                        "filepath": "Packs/SamplePack/Scripts/SampleScript/SampleScript.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships, targets only",
            ),
            pytest.param(
                Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.TARGETS,
                True,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack/Scripts/SampleScript/SampleScript.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships, targets only, mandatory only",
            ),
            pytest.param(
                Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
                RelationshipType.USES,
                ContentType.INTEGRATION,
                2,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml",
                        "mandatorily": False,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships, integrations only",
            ),
            pytest.param(
                Path(
                    "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml"
                ),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml",
                        "mandatorily": True,
                        "paths_count": 2,
                    },
                    {
                        "filepath": "Packs/SamplePack/Scripts/SampleScript/SampleScript.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                    {
                        "filepath": "Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships where depth=2 - 2 paths to SampleIntegration",
            ),
            pytest.param(
                Path(
                    "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml"
                ),
                RelationshipType.USES,
                ContentType.BASE_NODE,
                1,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                    {
                        "filepath": "Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml",
                        "mandatorily": True,
                        "paths_count": 1,
                    },
                ],
                id="Verify USES relationships where depth=1 - only 1 path to SampleIntegration,"
                " no path to SampleScript",
            ),
            pytest.param(
                Path(
                    "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml"
                ),
                RelationshipType.IMPORTS,
                ContentType.BASE_NODE,
                1,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack3/Scripts/TestApiModule/TestApiModule.yml",
                        "paths_count": 1,
                    },
                ],
                id="Verify IMPORTS relationship",
            ),
            pytest.param(
                Path(
                    "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml"
                ),
                RelationshipType.TESTED_BY,
                ContentType.BASE_NODE,
                1,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [
                    {
                        "filepath": "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml",
                        "paths_count": 1,
                    }
                ],
                id="Verify TESTED_BY relationship",
            ),
            pytest.param(
                Path("Packs/SamplePack3"),
                RelationshipType.DEPENDS_ON,
                ContentType.BASE_NODE,
                2,
                MarketplaceVersions.XSOAR,
                Direction.BOTH,
                False,
                False,
                [],
                [],
                id="Verify DEPENDS_ON relationships - don't include tests",
            ),
            pytest.param(
                Path("Packs/SamplePack3"),
                RelationshipType.DEPENDS_ON,
                ContentType.BASE_NODE,
                2,
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
                id="Verify DEPENDS_ON relationships - include tests",
            ),
        ],
    )
    def test_get_relationships(
        self,
        repository: ContentDTO,  # noqa: F811
        filepath: Path,
        relationship: RelationshipType,
        content_type: ContentType,
        depth: int,
        marketplace: MarketplaceVersions,
        direction: Direction,
        mandatory_only: bool,
        include_tests: bool,
        expected_sources: list,
        expected_targets: list,
    ) -> None:
        """
        Given:
            - A mocked model of a repository.
        When:
            - Running get_relationships_by_path() for the above test cases.
        Then:
            - Make sure the resulted sources and targets are as expected.
        """
        create_mini_content(repository)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            result = get_relationships_by_path(
                interface,
                input_filepath=filepath,
                relationship=relationship,
                content_type=content_type,
                depth=depth,
                marketplace=marketplace,
                direction=direction,
                mandatory_only=mandatory_only,
                include_tests=include_tests,
                include_deprecated=False,
                include_hidden=False,
            )
            sources, targets = result["sources"], result["targets"]
        compare(sources, expected_sources)
        compare(targets, expected_targets)
