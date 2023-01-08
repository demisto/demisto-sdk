import shutil
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Any, Callable, Dict, List
from zipfile import ZipFile

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph,
    stop_content_graph,
    update_content_graph,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    find_model_for_id,
    mock_classifier,
    mock_integration,
    mock_pack,
    mock_playbook,
    mock_relationship,
    mock_script,
    mock_test_playbook,
)
from demisto_sdk.commands.content_graph.tests.test_tools import TEST_DATA_PATH

GIT_PATH = Path(git_path())


# FIXTURES


@pytest.fixture(autouse=True)
def setup(mocker):
    """Auto-used fixture for setup before every test run"""
    mocker.patch(
        "demisto_sdk.commands.content_graph.objects.base_content.get_content_path",
        return_value=GIT_PATH,
    )
    mocker.patch.object(neo4j_service, "REPO_PATH", GIT_PATH)
    mocker.patch.object(ContentGraphInterface, "repo_path", GIT_PATH)
    stop_content_graph()


@pytest.fixture
def repository(mocker) -> ContentDTO:
    repository = ContentDTO(
        path=GIT_PATH,
        packs=[],
    )
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
            mock_relationship(
                "TestApiModule", ContentType.SCRIPT, "SamplePack2", ContentType.PACK
            ),
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "TestApiModule",
                ContentType.SCRIPT,
                "SampleScript2",
                ContentType.SCRIPT,
                mandatorily=True,
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
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


# HELPERS


def mock_dependency(source: str, target: str, mandatory: bool = True) -> Dict[str, Any]:
    return {
        "source_id": source,
        "source_type": ContentType.PACK,
        "target": target,
        "target_type": ContentType.PACK,
        "mandatorily": mandatory,
    }


def update_repository(
    repository: ContentDTO,
    commit_func: Callable[[ContentDTO], List[Pack]],
) -> List[str]:
    updated_packs = commit_func(repository)
    pack_ids_to_update = [pack.object_id for pack in updated_packs]
    repository.packs = [
        pack for pack in repository.packs if pack.object_id not in pack_ids_to_update
    ]
    repository.packs.extend(updated_packs)
    return pack_ids_to_update


def _get_pack_by_id(repository: ContentDTO, pack_id: str) -> Pack:
    for pack in repository.packs:
        if pack.object_id == pack_id:
            return pack
    raise ValueError(f"Pack {pack_id} does not exist in the repository.")


def dump_csv_import_files(csv_files_dir: Path) -> None:
    import_path = neo4j_service.get_neo4j_import_path().as_posix()
    if Path(import_path).is_dir():
        shutil.rmtree(import_path)
        copy_tree(csv_files_dir.as_posix(), import_path)


# COMPARISON HELPER FUNCTIONS


def compare(
    packs_from_content_dto: List[Pack],
    packs_from_graph: List[Pack],
    expected_added_dependencies: List[Dict[str, Any]],
    expected_removed_dependencies: List[Dict[str, Any]],
    after_update: bool,
) -> None:
    packs_from_content_dto.sort(key=lambda pack: pack.object_id)
    packs_from_graph.sort(key=lambda pack: pack.object_id)
    assert len(packs_from_content_dto) == len(packs_from_graph)
    for pack_a, pack_b in zip(packs_from_content_dto, packs_from_graph):
        assert pack_a.to_dict() == pack_b.to_dict()
        _compare_content_items(list(pack_a.content_items), list(pack_b.content_items))
        _compare_relationships(pack_a, pack_b)
    _verify_dependencies_existence(
        packs_from_graph, expected_added_dependencies, should_exist=after_update
    )
    _verify_dependencies_existence(
        packs_from_graph, expected_removed_dependencies, should_exist=not after_update
    )


def _compare_content_items(
    content_items_list_a: List[ContentItem], content_items_list_b: List[ContentItem]
) -> None:
    assert len(content_items_list_a) == len(content_items_list_b)
    for ci_a, ci_b in zip(content_items_list_a, content_items_list_b):
        assert ci_a.to_dict() == ci_b.to_dict()


def _compare_relationships(pack_a: Pack, pack_b: Pack) -> None:
    for relationship_type, relationships in pack_a.relationships.items():
        for relationship in relationships:
            content_item_source = find_model_for_id(
                [pack_b], relationship.get("source_id")
            )
            content_item_target_id = relationship.get("target")
            assert content_item_source
            assert content_item_target_id
            if relationship_type == RelationshipType.IN_PACK:
                assert (
                    content_item_source.in_pack
                ), f"{content_item_source.object_id} is not in pack."
                assert content_item_source.in_pack.object_id == content_item_target_id
            if relationship_type == RelationshipType.IMPORTS:
                assert (
                    content_item_source.imports[0].object_id == content_item_target_id
                )
            if relationship_type == RelationshipType.USES_BY_ID:
                assert (
                    content_item_source.uses[0].content_item.object_id
                    == content_item_target_id
                )
            if relationship_type == RelationshipType.TESTED_BY:
                assert (
                    content_item_source.tested_by[0].object_id == content_item_target_id
                )


def _verify_dependencies_existence(
    packs: List[Pack],
    dependencies: List[Dict[str, Any]],
    should_exist: bool,
) -> None:
    for dependency in dependencies:
        for pack in packs:
            if pack.object_id == dependency["source_id"]:
                if should_exist:
                    assert any(
                        r.target.object_id == dependency["target"]
                        for r in pack.depends_on
                    )
                else:
                    assert all(
                        r.target.object_id != dependency["target"]
                        for r in pack.depends_on
                    )
                break
        else:
            assert False


# TEST CASES (commit functions)


def _testcase1__pack3_pack4__script2_uses_script4(repository: ContentDTO) -> List[Pack]:
    """Test case for the following updates:
    * New pack: SamplePack4, with a script: SampleScript4
    * New relationship: SampleScript2 (of existing pack SamplePack3) USES SampleScript4 (of new pack SamplePack4)

    Returns:
        A list of the updated packs: pack3, pack4.
    """
    pack4_relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleScript4",
                ContentType.SCRIPT,
                "SamplePack4",
                ContentType.PACK,
            )
        ],
    }
    pack4 = mock_pack("SamplePack4")
    pack4.relationships = pack4_relationships
    pack4.content_items.script.append(mock_script("SampleScript4"))

    pack3 = _get_pack_by_id(repository, "SamplePack3")
    pack3.relationships.setdefault(RelationshipType.USES_BY_ID, []).append(
        mock_relationship(
            "SampleScript2",
            ContentType.SCRIPT,
            "SampleScript4",
            ContentType.SCRIPT,
        )
    )
    return [pack3, pack4]


def _testcase2__pack3__remove_relationship(repository: ContentDTO) -> List[Pack]:
    """Test case for the following update:
    * Remove relationship: TestApiModule (of pack SamplePack2) USES SampleScript2 (of pack SamplePack3)

    Returns:
        A list of the updated pack: pack2.
    """
    pack2 = _get_pack_by_id(repository, "SamplePack2")
    uses_relationships = pack2.relationships.get(RelationshipType.USES_BY_ID, [])
    for rel in uses_relationships:
        if rel["source_id"] == "TestApiModule" and rel["target"] == "SampleScript2":
            uses_relationships.remove(rel)
            break
    return [pack2]


# Test class


class TestUpdateContentGraph:
    def test_merge_graphs(self):
        """
        Given:
            - A content graph interface.
            - Valid neo4j CSV files of two repositories to import.
              * The first repository (content) has a single pack `SamplePack`, with:
                1. Integration `SampleIntegration` with a single command `test-command`.
                2. Classifier `SampleClassifier`, used by the integration.
              * The second repository (content-private) has a single pack `SamplePack4`, with:
                1. Integration `SampleIntegration4` with a single command `test-command`.
                   The integration uses `SampleClassifier` of SamplePack (from content repository).
        When:
            - Running update_graph() command.
        Then:
            - Make sure both repositories are imported successfully to the graph, i.e., the graph has:
              1. Two packs
              2. Two integrations, using the same (single) command
              3. One classifier
        """

        def get_nodes_count_by_type(
            interface: ContentGraphInterface,
            content_type: ContentType,
        ) -> int:
            return len(
                interface.search(
                    marketplace=MarketplaceVersions.XSOAR,
                    content_type=content_type,
                )
            )

        with ContentGraphInterface() as interface:
            dump_csv_import_files(
                TEST_DATA_PATH / "mock_import_files_multiple_repos__valid"
            )
            update_content_graph(interface, packs_to_update=[])
            assert get_nodes_count_by_type(interface, ContentType.PACK) == 2
            assert get_nodes_count_by_type(interface, ContentType.INTEGRATION) == 2
            assert get_nodes_count_by_type(interface, ContentType.COMMAND) == 1
            assert get_nodes_count_by_type(interface, ContentType.CLASSIFIER) == 1

    @pytest.mark.parametrize(
        "commit_func, expected_added_dependencies, expected_removed_dependencies",
        [
            pytest.param(
                _testcase1__pack3_pack4__script2_uses_script4,
                [mock_dependency("SamplePack3", "SamplePack4")],
                [],
                id="New pack with USES relationship, causing adding a dependency",
            ),
            pytest.param(
                _testcase2__pack3__remove_relationship,
                [],
                [mock_dependency("SamplePack2", "SamplePack3")],
                id="Remove USES relationship, causing removing a dependency",
            ),
        ],
    )
    def test_update_content_graph(
        self,
        tmp_path,
        repository: ContentDTO,
        commit_func: Callable[[ContentDTO], List[Pack]],
        expected_added_dependencies: List[Dict[str, Any]],
        expected_removed_dependencies: List[Dict[str, Any]],
    ):
        """
        Given:
            - A ContentDTO model representing the repository state on master branch.
            - A function representing a commit (an update of certain packs in the repository).
            - Lists of the expected added & removed pack dependencies after the update.
        When:
            - Running create_content_graph() on master.
            - Pushing a commit with the pack updates.
            - Running update_content_graph().
        Then:
            - Make sure the pack models from the interface are equal to the pack models from ContentDTO
                before and after the update.
            - Make sure the expected added dependencies actually don't exist before the update
                and exist after the update.
            - Make sure the expected removed dependencies actually exist before the update
                and don't exist after the update.
        """
        with ContentGraphInterface() as interface:
            # create the graph with dependencies
            create_content_graph(interface, dependencies=True, output_path=tmp_path)
            packs_from_graph = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )

            compare(
                repository.packs,
                packs_from_graph,
                expected_added_dependencies,
                expected_removed_dependencies,
                after_update=False,
            )

            # perform the update on ContentDTO
            pack_ids_to_update = update_repository(repository, commit_func)

            # update the graph accordingly
            update_content_graph(
                interface,
                packs_to_update=pack_ids_to_update,
                dependencies=True,
                output_path=tmp_path,
            )
            packs_from_graph = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )
            compare(
                repository.packs,
                packs_from_graph,
                expected_added_dependencies,
                expected_removed_dependencies,
                after_update=True,
            )
        # make sure that the output file zip is created
        assert Path.exists(tmp_path / "xsoar.zip")
        with ZipFile(tmp_path / "xsoar.zip", "r") as zip_obj:
            zip_obj.extractall(tmp_path / "extracted")
            # make sure that the extracted files are all .csv
            extracted_files = list(tmp_path.glob("extracted/*"))
            assert extracted_files
            assert all(file.suffix == ".csv" for file in extracted_files)
