from pathlib import Path
from typing import Any, Callable, Dict, List
from zipfile import ZipFile

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.commands.update import (
    update_content_graph,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Integration
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
def setup_method(mocker, tmp_path_factory):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc
    from demisto_sdk.commands.common.files.file import File

    bc.CONTENT_PATH = GIT_PATH
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", GIT_PATH)
    mocker.patch.object(
        File,
        "read_from_github_api",
        return_value={
            "docker_images": {
                "python3": {
                    "3.10.11.54799": {"python_version": "3.10.11"},
                    "3.10.12.63474": {"python_version": "3.10.11"},
                }
            }
        },
    )


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
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "test-command",
                ContentType.COMMAND,
            ),
        ],
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

    def mock__create_content_dto(packs_to_update: List[str]) -> List[ContentDTO]:
        if not packs_to_update:
            return [repository]
        repo_copy = repository.copy()
        repo_copy.packs = [p for p in repo_copy.packs if p.object_id in packs_to_update]
        return [repo_copy]

    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        side_effect=mock__create_content_dto,
    )
    return repository


@pytest.fixture
def external_repository(mocker) -> ContentDTO:
    repository = ContentDTO(
        path=GIT_PATH,
        packs=[],
    )

    pack1 = mock_pack("ExternalPack")
    repository.packs.extend([pack1])

    def mock__create_content_dto(packs_to_update: List[str]) -> List[ContentDTO]:
        if not packs_to_update:
            return [repository]
        repo_copy = repository.copy()
        repo_copy.packs = [p for p in repo_copy.packs if p.object_id in packs_to_update]
        return [repo_copy]

    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        side_effect=mock__create_content_dto,
    )

    def mock__create_content_dto(packs_to_update: List[str]) -> List[ContentDTO]:
        if not packs_to_update:
            return [repository]
        repo_copy = repository.copy()
        repo_copy.packs = [p for p in repo_copy.packs if p.object_id in packs_to_update]
        return [repo_copy]

    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        side_effect=mock__create_content_dto,
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
    content_items_list_a = sorted(content_items_list_a, key=lambda obj: obj.node_id)
    content_items_list_b = sorted(content_items_list_b, key=lambda obj: obj.node_id)
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
                    content_item_source.uses[0].content_item_to.object_id
                    == content_item_target_id
                ) or any(
                    [
                        isinstance(uses_rel.content_item_to, Integration)
                        and uses_rel.content_item_to.commands[0].name
                        == content_item_target_id
                        for uses_rel in content_item_source.uses
                    ]
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
                        r.content_item_to.object_id == dependency["target"]
                        for r in pack.depends_on
                    )
                else:
                    assert all(
                        r.content_item_to.object_id != dependency["target"]
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


def _testcase3__no_change(_: ContentDTO) -> List[Pack]:
    """Test case for a commit diff without update."""
    return []


def _testcase4__new_integration_with_existing_command(
    repository: ContentDTO,
) -> List[Pack]:
    """Test case for the following update:
    * New integration: SampleIntegration2 in SamplePack
    * New command: test-command (node already exists for SampleIntegration2)

    Returns:
        A list of the updated pack: pack.
    """
    pack = _get_pack_by_id(repository, "SamplePack")
    pack.content_items.integration.append(mock_integration("SampleIntegration2"))
    pack.relationships.setdefault(RelationshipType.IN_PACK, []).append(
        mock_relationship(
            "SampleIntegration2",
            ContentType.INTEGRATION,
            "SamplePack",
            ContentType.PACK,
        )
    )
    pack.relationships.setdefault(RelationshipType.HAS_COMMAND, []).append(
        mock_relationship(
            "SampleIntegration2",
            ContentType.INTEGRATION,
            "test-command",
            ContentType.COMMAND,
            name="test-command",
            description="",
            deprecated=False,
        )
    )
    return [pack]


def _testcase5__move_script_from_pack3_to_pack1(repository: ContentDTO) -> List[Pack]:
    """Test case for the following update:
    * Moved SampleScript2 from SamplePack3 to SamplePack.

    Returns:
        A list of the updated packs: pack2 and pack3.
    """
    pack1 = _get_pack_by_id(repository, "SamplePack")
    pack3 = _get_pack_by_id(repository, "SamplePack3")
    pack1.content_items.script.append(pack3.content_items.script[0])
    pack3.content_items.script = []
    in_pack_relationships = pack3.relationships.get(RelationshipType.IN_PACK, [])
    for rel in in_pack_relationships:
        if rel["source_id"] == "SampleScript2" and rel["target"] == "SamplePack3":
            in_pack_relationships.remove(rel)
            break
    pack1.relationships.setdefault(RelationshipType.IN_PACK, []).append(
        mock_relationship(
            "SampleScript2",
            ContentType.SCRIPT,
            "SamplePack",
            ContentType.PACK,
        )
    )
    return [pack1, pack3]


def _testcase6__move_script_from_pack3_to_pack2(repository: ContentDTO) -> List[Pack]:
    """Test case for the following update:
    * Moved SampleScript2 from SamplePack3 to SamplePack2.

    Returns:
        A list of the updated packs: pack2 and pack3.
    """
    pack2 = _get_pack_by_id(repository, "SamplePack2")
    pack3 = _get_pack_by_id(repository, "SamplePack3")
    pack2.content_items.script.append(pack3.content_items.script[0])
    pack3.content_items.script = []
    pack2.relationships.setdefault(RelationshipType.IN_PACK, []).append(
        mock_relationship(
            "SampleScript2",
            ContentType.SCRIPT,
            "SamplePack2",
            ContentType.PACK,
        )
    )
    in_pack_relationships = pack3.relationships.get(RelationshipType.IN_PACK, [])
    for rel in in_pack_relationships:
        if rel["source_id"] == "SampleScript2" and rel["target"] == "SamplePack3":
            in_pack_relationships.remove(rel)
            break
    return [pack2, pack3]


def _testcase7__changed_script2_fromversion(repository: ContentDTO) -> List[Pack]:
    """Test case for the following update:
    * SampleScript2 - changed fromversion

    Returns:
        A list of the updated pack: pack3.
    """
    new_fromversion = "7.0.0"
    pack3 = _get_pack_by_id(repository, "SamplePack3")
    pack3.content_items.script[0].fromversion = new_fromversion
    in_pack_relationships = pack3.relationships.get(RelationshipType.IN_PACK, [])
    for rel in in_pack_relationships:
        if rel["source_id"] == "SampleScript2" and rel["target"] == "SamplePack3":
            rel["source_fromversion"] = new_fromversion
            break
    return [pack3]


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
            update_content_graph(
                interface,
                packs_to_update=[],
                imported_path=TEST_DATA_PATH
                / "mock_import_files_multiple_repos__valid"
                / "valid_graph.zip",
            )
            assert get_nodes_count_by_type(interface, ContentType.PACK) == 2
            assert get_nodes_count_by_type(interface, ContentType.INTEGRATION) == 2
            assert get_nodes_count_by_type(interface, ContentType.COMMAND) == 1
            assert get_nodes_count_by_type(interface, ContentType.CLASSIFIER) == 1

    data_test_update_content_graph = [
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
        pytest.param(
            _testcase3__no_change,
            [],
            [],
            id="No change in repository",
        ),
        pytest.param(
            _testcase4__new_integration_with_existing_command,
            [],
            [],
            id="New integration with existing command test-command",
        ),
        pytest.param(
            _testcase5__move_script_from_pack3_to_pack1,
            [mock_dependency("SamplePack2", "SamplePack")],
            [mock_dependency("SamplePack2", "SamplePack3")],
            id="Moved script - dependency pack2 -> pack3 changed to pack2 -> pack1",
        ),
        pytest.param(
            _testcase6__move_script_from_pack3_to_pack2,
            [],
            [mock_dependency("SamplePack2", "SamplePack3")],
            id="Moved script - removed dependency between pack2 and pack3",
        ),
        pytest.param(
            _testcase7__changed_script2_fromversion,
            [],
            [],
            id="Changed fromversion of script",
        ),
    ]

    @pytest.mark.parametrize(
        "commit_func, expected_added_dependencies, expected_removed_dependencies",
        data_test_update_content_graph,
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
            assert all(
                file.suffix == ".graphml"
                or file.name == "metadata.json"
                or file.name == "depends_on.json"
                for file in extracted_files
            )

    @pytest.mark.parametrize(
        "commit_func, expected_added_dependencies, expected_removed_dependencies",
        data_test_update_content_graph,
    )
    def test_create_content_graph_if_needed(
        self,
        tmp_path,
        repository: ContentDTO,
        mocker,
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
        import demisto_sdk.commands.content_graph.commands.update as update

        create_content_graph_spy = mocker.spy(update, "create_content_graph")

        with ContentGraphInterface() as interface:
            # create the graph with dependencies
            update.create_content_graph(
                interface, dependencies=True, output_path=tmp_path
            )
            packs_from_graph = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )

            file_added = (
                Path(__file__).parent.parent / "parsers" / "content_graph_test.txt"
            )
            file_added.write_text(
                "this file is created by a test in "
                "demisto_sdk/commands/content_graph/tests/update_content_graph_test.py"
                " and should be removed when the test passes"
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
            update.update_content_graph(
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
        file_added.unlink()
        assert create_content_graph_spy.call_count == 2
        # make sure that the output file zip is created
        assert Path.exists(tmp_path / "xsoar.zip")
        with ZipFile(tmp_path / "xsoar.zip", "r") as zip_obj:
            zip_obj.extractall(tmp_path / "extracted")
            # make sure that the extracted files are all .csv
            extracted_files = list(tmp_path.glob("extracted/*"))
            assert extracted_files
            assert all(
                file.suffix == ".graphml"
                or file.name == "metadata.json"
                or file.name == "depends_on.json"
                for file in extracted_files
            )

    def test_update_content_graph_external_repo(self, mocker, external_repository):
        """
        Given:
            - A content graph interface.
            - Valid neo4j CSV files of two repositories to import, with two repository, each with one pack.
            - an external repository with one pack
        When:
            - Running update_graph() command.
        Then:
            - Make sure that the graph has three packs now.
        """

        with ContentGraphInterface() as interface:
            mocker.patch(
                "demisto_sdk.commands.content_graph.commands.update.is_external_repository",
                return_value=True,
            )
            mocker.patch(
                "demisto_sdk.commands.content_graph.commands.update.get_all_repo_pack_ids",
                return_value=["ExternalPack"],
            )

            update_content_graph(
                interface,
                packs_to_update=[],
                imported_path=TEST_DATA_PATH
                / "mock_import_files_multiple_repos__valid"
                / "valid_graph.zip",
            )
            packs_from_graph = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )
            assert len(packs_from_graph) == 3
