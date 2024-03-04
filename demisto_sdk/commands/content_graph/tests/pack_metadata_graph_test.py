from pathlib import Path

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
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


@pytest.fixture(autouse=True)
def setup_method(mocker, tmp_path_factory, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))


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
        - A repository with a pack TestPack, containing multiple content items.
    When:
        - Dumping the pack and pack metadata.json for marketplace `xsoar`.
    Then:
        - Make sure the the metadata value as expected.
        - Make sure the `serverMinVersion` is the minimum content item fromversion value except the test playbook.
        - Make sure that along 3 versions of a playbook, only the latest is in the metadata.
        - Make sure the script tags are in the pack metadata tags.
    """
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    mocker.patch.object(PackMetadata, "_get_tags_from_landing_page", return_value=set())

    pack = repo.create_pack("TestPack")
    pack.pack_metadata.write_json(load_json("pack_metadata.json"))

    integration = pack.create_integration()
    integration.create_default_integration(
        name="TestIntegration", commands=["test-command1", "test-command2"]
    )
    integration.yml.update(
        {
            "display": "Test Integration",
            "category": "Authentication & Identity Management",
            "description": "integration  description\n  - for  \n    - example  ",
            "fromversion": "6.8.0",
        }
    )
    integration.yml.update(
        {
            "isfetch": True,
            "type": "python3",
        },
        key_dict_to_update="script",
    )

    script = pack.create_script()
    script.create_default_script("TestScript")
    script.yml.update({"tags": ["transformer", "filter"], "fromversion": "6.5.0"})

    playbook1 = pack.create_playbook()
    playbook1.create_default_playbook(name="MyPlaybook")
    playbook1.yml.update({"fromversion": "6.5.0", "toversion": "6.7.9"})
    playbook2 = pack.create_playbook()
    playbook2.create_default_playbook(name="MyPlaybook")
    playbook2.yml.update({"fromversion": "6.8.0", "toversion": "6.9.9"})
    playbook3 = pack.create_playbook()
    playbook3.create_default_playbook(name="MyPlaybook")
    playbook3.yml.update({"fromversion": "6.10.0"})

    test_playbook = pack.create_test_playbook()
    test_playbook.create_default_test_playbook(name="TestTestPlaybook")
    test_playbook.yml.update({"fromversion": "6.2.0"})

    with ContentGraphInterface() as interface:
        create_content_graph(interface, output_path=tmp_path)
        content_cto = interface.marshal_graph(MarketplaceVersions.XSOAR)

    with ChangeCWD(repo.path):
        content_cto.dump(tmp_path, MarketplaceVersions.XSOAR, zip=False)

    assert (tmp_path / "TestPack" / "metadata.json").exists()
    metadata = get_json(tmp_path / "TestPack" / "metadata.json")

    assert metadata.get("id") == "TestPack"
    assert metadata.get("name") == "HelloWorld"
    assert metadata.get("display_name") == "HelloWorld"
    assert (
        metadata.get("description")
        == "This is the Hello World integration for getting started."
    )
    assert metadata.get("legacy") is True
    assert metadata.get("support") == "community"
    assert (
        metadata.get("supportDetails", {}).get("url")
        == "https://www.paloaltonetworks.com/cortex"
    )
    assert "email" not in metadata.get("supportDetails", {})
    assert (
        metadata.get("eulaLink")
        == "https://github.com/demisto/content/blob/master/LICENSE"
    )
    assert metadata.get("author") == "Cortex XSOAR"
    assert metadata.get("authorImage") == "content/packs/TestPack/Author_image.png"
    assert metadata.get("certification") == "verified"
    assert metadata.get("price") == 0
    assert metadata.get("hidden") is False
    assert metadata.get("serverMinVersion") == "6.5.0"
    assert metadata.get("currentVersion") == "1.2.12"
    assert metadata.get("versionInfo") == ""
    assert metadata.get("downloads") == 0
    assert sorted(metadata.get("tags", [])) == sorted(
        ["TIM", "Transformer", "Use Case", "Filter"]
    )
    assert metadata.get("categories") == ["Utilities"]
    assert metadata.get("useCases") == ["Identity And Access Management"]
    assert metadata.get("keywords") == ["common"]
    assert metadata.get("searchRank") == 0
    assert metadata.get("excludedDependencies") == []
    assert metadata.get("videos") == []
    assert metadata.get("modules") == []
    assert metadata.get("integrations") == []

    metadata_integration = metadata.get("contentItems", {}).get("integration", [{}])[0]
    assert (
        metadata_integration.get("category") == "Authentication & Identity Management"
    )
    assert len(metadata_integration.get("commands", [])) == 3
    assert (
        metadata_integration.get("description")
        == "integration description\n  - for \n    - example "
    )
    assert metadata_integration.get("fromversion") == "6.8.0"
    assert metadata_integration.get("id") == "TestIntegration"
    assert metadata_integration.get("isfetch") is True
    assert (
        metadata_integration.get("name") == "Test Integration (Community Contribution)"
    )

    metadata_playbook = metadata.get("contentItems", {}).get("playbook", [{}])[0]
    assert metadata_playbook.get("fromversion") == "6.10.0"
    assert metadata_playbook.get("id") == "MyPlaybook"
    assert metadata_playbook.get("name") == "MyPlaybook"


def test_pack_metadata_marketplacev2(repo: Repo, tmp_path: Path, mocker):
    """
    Given:
        - A repository with a pack TestPack, containing multiple content items.
    When:
        - Dumping the pack and pack metadata.json for marketplace `marketplacev2`.
    Then:
        - Make sure the the metadata value as expected.
        - Make sure that along 3 versions of a playbook, only the latest is in the metadata.
        - Make sure the script tags are in the pack metadata tags.
    """
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    mocker.patch.object(PackMetadata, "_get_tags_from_landing_page", return_value=set())

    pack = repo.create_pack("TestPack")
    pack.pack_metadata.write_json(load_json("pack_metadata2.json"))

    integration = pack.create_integration()
    integration.create_default_integration(name="TestIntegration")
    integration.yml.update(
        {
            "display": "Test Integration",
            "fromversion": "6.8.0",
        }
    )
    integration.yml.update(
        {
            "isfetchevents": True,
            "type": "python3",
        },
        key_dict_to_update="script",
    )

    playbook1 = pack.create_playbook()
    playbook1.create_default_playbook(name="MyPlaybook")
    playbook1.yml.update({"fromversion": "6.5.0", "toversion": "6.7.9"})
    playbook2 = pack.create_playbook()
    playbook2.create_default_playbook(name="MyPlaybook")
    playbook2.yml.update({"fromversion": "6.10.0"})

    pack.create_modeling_rule(
        name="MyModelingRule",
        yml={
            "id": "my_modeling_rule",
            "name": "My Modeling Rule",
            "fromversion": "6.8.0",
            "toversion": "6.9.9",
        },
    )
    pack.create_modeling_rule(
        name="MyModelingRule_1_3",
        yml={
            "id": "my_ModelingRule",
            "name": "My Modeling Rule",
            "fromversion": "6.10.0",
        },
    )

    with ContentGraphInterface() as interface:
        create_content_graph(interface, output_path=tmp_path)
        content_cto = interface.marshal_graph(MarketplaceVersions.MarketplaceV2)

    with ChangeCWD(repo.path):
        content_cto.dump(tmp_path, MarketplaceVersions.MarketplaceV2, zip=False)

    assert (tmp_path / "TestPack" / "metadata.json").exists()
    metadata = get_json(tmp_path / "TestPack" / "metadata.json")

    assert metadata.get("id") == "TestPack"
    assert metadata.get("name") == "HelloWorld2"
    assert metadata.get("display_name") == "HelloWorld2"
    assert (
        metadata.get("description")
        == "This is the Hello World 2 integration for getting started."
    )
    assert metadata.get("legacy") is True
    assert metadata.get("support") == "xsoar"
    assert (
        metadata.get("supportDetails", {}).get("url")
        == "https://www.paloaltonetworks.com/cortex"
    )
    assert "email" not in metadata.get("supportDetails", {})
    assert (
        metadata.get("eulaLink")
        == "https://github.com/demisto/content/blob/master/LICENSE"
    )
    assert metadata.get("author") == "Cortex XSIAM"
    assert metadata.get("authorImage") == "content/packs/TestPack/Author_image.png"
    assert metadata.get("certification") == "certified"
    assert metadata.get("hidden") is False
    assert metadata.get("serverMinVersion") == "6.5.0"
    assert metadata.get("currentVersion") == "1.2.13"
    assert sorted(metadata.get("tags", [])) == sorted(["Data Source", "Collection"])
    assert metadata.get("categories") == ["Utilities"]

    metadata_integration = metadata.get("contentItems", {}).get("integration", [{}])[0]
    assert len(metadata_integration.get("commands", [])) == 1
    assert metadata_integration.get("fromversion") == "6.8.0"
    assert metadata_integration.get("id") == "TestIntegration"
    assert metadata_integration.get("isfetchevents") is True
    assert metadata_integration.get("name") == "Test Integration"

    metadata_playbook = metadata.get("contentItems", {}).get("playbook", [{}])[0]
    assert metadata_playbook.get("fromversion") == "6.10.0"
    assert metadata_playbook.get("id") == "MyPlaybook"
    assert metadata_playbook.get("name") == "MyPlaybook"

    metadata_modeling_rule = metadata.get("contentItems", {}).get("modelingrule", [{}])[
        0
    ]
    assert metadata_modeling_rule.get("fromversion") == "6.10.0"
    assert metadata_modeling_rule.get("id") == "my_ModelingRule"
    assert metadata_modeling_rule.get("name") == "My Modeling Rule"
