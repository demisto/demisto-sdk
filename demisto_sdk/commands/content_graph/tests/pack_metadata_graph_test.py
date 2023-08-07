from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


@pytest.fixture
def repository(mocker):
    repository = ContentDTO(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        return_value=[repository],
    )
    return repository


def test_pack_metadata_xsoar(repo: Repo, tmp_path: Path, mocker):
    """
    Given:
        - A repository with a pack TestPack, containing an integration TestIntegration.
    When:
        - Running create_content_graph()
    Then:
        - Make sure the service remains available by querying for all content items in the graph.
        - Make sure there is a single integration in the query response.
    """
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    mocker.patch.object(PackMetadata, "_get_tags_from_landing_page", retrun_value={})

    pack = repo.create_pack("TestPack")
    pack.pack_metadata.write_json(load_json("pack_metadata.json"))
    pack.create_integration(
        name="TestIntegration",
        yml={
            "script": {
                "commands": [
                    {
                        "name": "test-command1",
                    },
                    {
                        "name": "test-command2",
                    },
                ],
                "fromversion": "6.8.0",
                "description": "integration  description\n - for  \n    - example ",
                "category": "Authentication & Identity Management",
                "display": "Test Integration",
                "isfetch": True,
            }
        },
    )
    pack.create_script(
        name="TestScript",
        yml={"tags": ["transformer", "filter"], "fromversion": "6.5.0"},
    )
    pack.create_test_playbook("TestTestPlaybook", yml={"fromversion": "6.2.0"})

    with ContentGraphInterface() as interface:
        create_content_graph(interface, output_path=tmp_path)
        content_cto = interface.marshal_graph(MarketplaceVersions.XSOAR)

    with ChangeCWD(repo.path):
        content_cto.dump(tmp_path, MarketplaceVersions.XSOAR, zip=False)

    assert (tmp_path / "TestPack" / "metadata.json").exists()
    metadata = get_json(tmp_path / "TestPack" / "metadata.json")

    assert metadata.get("id") == "TestPack"
    assert metadata.get("name") == "HelloWorld"
    assert (
        metadata.get("description")
        == "This is the Hello World integration for getting started."
    )
    assert metadata.get("created") == ""
    assert metadata.get("updated") == ""
    assert metadata.get("legacy") is True
    assert metadata.get("support") == "community"
    assert (
        metadata.get("supportDetails", {}).get("url")
        == "https://www.paloaltonetworks.com/cortex"
    )
    assert metadata.get("supportDetails", {}).get("email") == ""
    assert (
        metadata.get("eulaLink")
        == "https://github.com/demisto/content/blob/master/LICENSE"
    )
    assert metadata.get("author") == "Cortex XSOAR"
    assert metadata.get("authorImage") == "content/packs/HelloWorld/Author_image.png"
    assert metadata.get("certification") == "verified"
    assert metadata.get("price") == 0
    assert metadata.get("hidden") is False
    assert metadata.get("serverMinVersion") == "6.5.0"
    assert metadata.get("currentVersion") == "1.2.12"
    assert metadata.get("versionInfo") == ""
    assert metadata.get("commit") == ""
    assert metadata.get("downloads") == 0
    assert metadata.get("tags") == ["TIM", "Transformer", "Filter"]
    assert metadata.get("categories") == ["Utilities"]
    assert metadata.get("useCases") == ["Identity and Access Management"]
    assert metadata.get("keywords") == []
    assert metadata.get("searchRank") == 0
    assert metadata.get("excludedDependencies") == []
    assert metadata.get("videos") == []
    assert metadata.get("modules") == []
    assert metadata.get("integrations") == []

    expected_integration_summary = {
        "category": "Authentication & Identity Management",
        "commands": [
            {
                "deprecated": False,
                "description": "",
                "id": "",
                "name": "test-command1",
            },
            {
                "deprecated": False,
                "description": "",
                "id": "",
                "name": "test-command2",
            },
        ],
        "deprecated": False,
        "description": "integration description\n - for \n    - example ",
        "fromversion": "6.8.0",
        "id": "TestIntegration",
        "isfetch": True,
        "isfetchevents": False,
        "name": "Test Integration",
        "toversion": "",
    }

    assert (
        metadata.get("contentItems", {}).get("integration", [{}])[0]
        == expected_integration_summary
    )
