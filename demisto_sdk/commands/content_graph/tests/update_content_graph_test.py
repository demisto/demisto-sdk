from pathlib import Path
from typing import Any, Dict, List

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import NEO4J_FOLDER, ContentType, RelationshipType
from demisto_sdk.commands.content_graph.content_graph_commands import create_content_graph, update_content_graph
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo

# Fixtures for mock content object models


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))


@pytest.fixture
def repository(mocker):
    repository = ContentDTO(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


def mock_pack(name: str = "SamplePack"):
    return Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=Path("/dummypath"),
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        created="",
        updated="",
        support="",
        email="",
        url="",
        author="",
        certification="",
        hidden=False,
        server_min_version="",
        current_version="1.0.0",
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems=[],
    )


def mock_integration(name: str = "SampleIntegration"):
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        category="blabla",
        commands=[Command(name="test-command", description="")],
    )


def mock_script(name: str = "SampleScript"):
    return Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        description="",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
    )


def mock_classifier(name: str = "SampleClassifier"):
    return Classifier(
        id=name,
        content_type=ContentType.CLASSIFIER,
        node_id=f"{ContentType.CLASSIFIER}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        description="",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
    )


def mock_playbook(name: str = "SamplePlaybook"):
    return Playbook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        is_test=False,
    )


def mock_test_playbook(name: str = "SampleTestPlaybook"):
    return TestPlaybook(
        id=name,
        # content_type=ContentType.TEST_PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        is_test=True,
    )


# HELPERS


def mock_relationship(
    source: str,
    source_type: ContentType,
    target: str,
    target_type: ContentType,
    source_fromversion: str = "5.0.0",
    source_marketplaces: List[str] = [MarketplaceVersions.XSOAR],
    **kwargs,
) -> Dict[str, Any]:
    rel = {
        "source_id": source,
        "source_type": source_type,
        "source_fromversion": source_fromversion,
        "source_marketplaces": source_marketplaces,
        "target": target,
        "target_type": target_type,
    }
    rel.update(kwargs)
    return rel


def find_model_for_id(packs: List[Pack], source_id: str):
    for pack in packs:
        if pack.object_id == source_id:
            return pack
        for content_item in pack.content_items:
            if content_item.object_id == source_id:
                return content_item
            if isinstance(content_item, Integration):
                for command in content_item.commands:
                    if command.name == source_id:
                        return command
    return None


def create_mini_content(repository: ContentDTO):
    """Created a content repo with three packs and relationships§

    Args:
        repository (ContentDTO): the content dto to populate
    """
    relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SamplePack",
                ContentType.PACK,
            ),
            mock_relationship(
                "SampleScript",
                ContentType.SCRIPT,
                "SamplePack",
                ContentType.PACK,
            ),
        ],
        RelationshipType.HAS_COMMAND: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "test-command",
                ContentType.COMMAND,
                name="test-command",
                description="",
                deprecated=False,
            )
        ],
        RelationshipType.IMPORTS: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "TestApiModule",
                ContentType.SCRIPT,
            )
        ],
        RelationshipType.TESTED_BY: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SampleTestPlaybook",
                ContentType.TEST_PLAYBOOK,
            )
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SampleClassifier",
                ContentType.CLASSIFIER,
                mandatorily=True,
            ),
        ],
    }
    relationship_pack2 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleClassifier",
                ContentType.CLASSIFIER,
                "SamplePack2",
                ContentType.PACK,
            ),
            mock_relationship(
                "SampleTestPlaybook",
                ContentType.TEST_PLAYBOOK,
                "SamplePack2",
                ContentType.PACK,
            ),
            mock_relationship("TestApiModule", ContentType.SCRIPT, "SamplePack2", ContentType.PACK),
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "TestApiModule", ContentType.SCRIPT, "SampleScript2", ContentType.SCRIPT, mandatorily=True
            ),
        ],
    }
    relationship_pack3 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "SamplePack3",
                ContentType.PACK,
            ),
            mock_relationship(
                "SampleScript2",
                ContentType.SCRIPT,
                "SamplePack3",
                ContentType.PACK,
            ),
        ]
    }
    pack1 = mock_pack()
    pack2 = mock_pack("SamplePack2")
    pack3 = mock_pack("SamplePack3")
    pack1.relationships = relationships
    pack2.relationships = relationship_pack2
    pack3.relationships = relationship_pack3
    pack1.content_items.integration.append(mock_integration())
    pack1.content_items.script.append(mock_script())
    pack2.content_items.script.append(mock_script("TestApiModule"))
    pack2.content_items.classifier.append(mock_classifier())
    pack2.content_items.test_playbook.append(mock_test_playbook())
    pack3.content_items.playbook.append(mock_playbook())
    pack3.content_items.script.append(mock_script("SampleScript2"))
    repository.packs.extend([pack1, pack2, pack3])


class TestUpdateContentGraph:
    def _test_create_content_graph_end_to_end(self, repo: Repo, start_service: bool) -> Repo:
        import demisto_sdk.commands.content_graph.objects.repository as repo_module

        repo_module.USE_FUTURE = False
        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        integration = pack.create_integration()
        integration.create_default_integration("TestIntegration", ["test-command1", "test-command2"])
        script = pack.create_script()
        api_module = pack.create_script()
        script.create_default_script("SampleScript")
        api_module.create_default_script("TestApiModule")

        pack.create_classifier(name="SampleClassifier", content=load_json("classifier.json"))

        with ContentGraphInterface(start_service=start_service) as interface:
            create_content_graph(interface, export=True)
        return repo

    def _test_update_content_graph_end_to_end(self, repo: Repo, start_service: bool, tmp_path: Path):
        import demisto_sdk.commands.content_graph.objects.repository as repo_module

        repo_module.USE_FUTURE = False
        pack = repo.create_pack("TestPack2")
        pack.pack_metadata.write_json(load_json("pack_metadata2.json"))
        script = pack.create_script()
        script.create_default_script("SampleScript2")
        script.code.write("execute_command('SampleScript')")

        with ContentGraphInterface(start_service=start_service) as interface:
            update_content_graph(interface, packs_to_update=['TestPack2'])
            packs = interface.search(marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK)
            integrations = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.INTEGRATION,
            )
            all_content_items = interface.search(marketplace=MarketplaceVersions.XSOAR)
            content_cto = interface.marshal_graph(MarketplaceVersions.XSOAR)
        for pack_node in packs:
            print(pack_node)
        assert len(packs) == 2
        assert len(integrations) == 1
        assert len(all_content_items) == 10

        # TestPack assertions (created before create_content_graph())
        first_pack = packs[0] if packs[0].object_id == "TestPack" else packs[1]
        # make sure that data from pack_metadata.json updated
        assert first_pack.name == "HelloWorld"
        assert first_pack.support == "community"
        assert len(first_pack.content_items.integration) == 1
        returned_integration = first_pack.content_items.integration[0]
        assert returned_integration == integrations[0]
        assert returned_integration.name == "TestIntegration"
        assert {command.name for command in returned_integration.commands} == {
            "test-command",
            "test-command1",
            "test-command2",
        }
        returned_scripts = {script.object_id for script in first_pack.content_items.script}
        assert returned_scripts == {"SampleScript", "TestApiModule"}

        # TestPack2 assertions (created before update_content_graph())
        second_pack = packs[0] if packs[0].object_id == "TestPack2" else packs[1]
        assert second_pack.name == "HelloWorld2"
        assert len(second_pack.content_items.script) == 1
        second_pack_script = second_pack.content_items.script[0]
        assert len(second_pack_script.uses) == 1
        assert second_pack_script.uses[0].target.object_id == "SampleScript"

        content_cto.dump(tmp_path, MarketplaceVersions.XSOAR, zip=False)
        assert Path.exists(tmp_path / "TestPack")
        assert Path.exists(tmp_path / "TestPack" / "metadata.json")
        assert Path.exists(tmp_path / "TestPack" / "Integrations" / "integration-integration_0.yml")
        assert Path.exists(tmp_path / "TestPack" / "Scripts" / "script-script0.yml")
        assert Path.exists(tmp_path / "TestPack" / "Scripts" / "script-script1.yml")
        assert Path.exists(tmp_path / "TestPack2")

        assert any((Path(repo.path) / NEO4J_FOLDER / "import").iterdir())

    def test_update_content_graph_end_to_end_with_existing_service(self, repo: Repo, tmp_path: Path):
        """
        Given:
            - A repository with a pack TestPack, containing a script SampleScript.
        When:
            - Running create_content_graph() with a new service.
            - Adding to the repository the pack TestPack2, containing a script that uses SampleScript.
            - Running update_content_graph() with the same service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure TestPack content items are returned in the query response.
            - Make sure TestPack2 content items and the USES relationship are returned in the query response.

        """
        repo = self._test_create_content_graph_end_to_end(repo, start_service=True)
        self._test_update_content_graph_end_to_end(repo, start_service=False, tmp_path=tmp_path)

    def test_update_content_graph_end_to_end_with_new_service(self, repo: Repo, tmp_path: Path):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with an existing, running service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        repo = self._test_create_content_graph_end_to_end(repo, start_service=True)
        self._test_update_content_graph_end_to_end(repo, start_service=True, tmp_path=tmp_path)
