# from pathlib import Path

# from demisto_sdk.commands.content_graph.commands.create import (
#     create_content_graph,
# )
# from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
# from demisto_sdk.commands.content_graph.interface import (
#     ContentGraphInterface,
# )
# from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
# from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
#     mock_integration,
#     mock_pack,
#     mock_relationship,
#     mock_script,
#     mock_test_playbook,
#     repository,
#     setup,
# )


# def create_mini_content(repository: ContentDTO):
#     """Creates a content repo with three packs and relationships§

#     Args:
#         repository (ContentDTO): the content dto to populate
#     """
#     relationships = {
#         RelationshipType.IN_PACK: [
#             mock_relationship(
#                 "SampleIntegration",
#                 ContentType.INTEGRATION,
#                 "SamplePack",
#                 ContentType.PACK,
#             ),
#             mock_relationship(
#                 "SampleScript",
#                 ContentType.SCRIPT,
#                 "SamplePack",
#                 ContentType.PACK,
#             ),
#         ],
#         RelationshipType.HAS_COMMAND: [
#             mock_relationship(
#                 "SampleIntegration",
#                 ContentType.INTEGRATION,
#                 "test-command",
#                 ContentType.COMMAND,
#                 name="test-command",
#                 description="",
#                 deprecated=False,
#             )
#         ],
#         RelationshipType.IMPORTS: [
#             mock_relationship(
#                 "SampleIntegration",
#                 ContentType.INTEGRATION,
#                 "TestApiModule",
#                 ContentType.SCRIPT,
#             )
#         ],
#         RelationshipType.TESTED_BY: [
#             mock_relationship(
#                 "SampleIntegration",
#                 ContentType.INTEGRATION,
#                 "SampleTestPlaybook",
#                 ContentType.TEST_PLAYBOOK,
#             )
#         ],
#     }
#     relationship_pack2 = {
#         RelationshipType.IN_PACK: [
#             mock_relationship(
#                 "SampleClassifier",
#                 ContentType.CLASSIFIER,
#                 "SamplePack2",
#                 ContentType.PACK,
#             ),
#             mock_relationship(
#                 "SampleTestPlaybook",
#                 ContentType.TEST_PLAYBOOK,
#                 "SamplePack2",
#                 ContentType.PACK,
#             ),
#             mock_relationship(
#                 "TestApiModule", ContentType.SCRIPT, "SamplePack2", ContentType.PACK
#             ),
#         ],
#         RelationshipType.USES_BY_ID: [
#             mock_relationship(
#                 "TestApiModule",
#                 ContentType.SCRIPT,
#                 "SampleScript2",
#                 ContentType.SCRIPT,
#                 mandatorily=True,
#             ),
#             mock_relationship(
#                 "SampleTestPlaybook",
#                 ContentType.TEST_PLAYBOOK,
#                 "SampleIntegration",
#                 ContentType.INTEGRATION,
#             ),
#         ],
#     }
#     relationship_pack3 = {
#         RelationshipType.IN_PACK: [
#             mock_relationship(
#                 "SampleScript2",
#                 ContentType.SCRIPT,
#                 "SamplePack3",
#                 ContentType.PACK,
#             ),
#         ]
#     }
#     pack1 = mock_pack("SamplePack")
#     pack2 = mock_pack("SamplePack2")
#     pack3 = mock_pack("SamplePack3")
#     pack1.relationships = relationships
#     pack2.relationships = relationship_pack2
#     pack3.relationships = relationship_pack3
#     pack1.content_items.integration.append(mock_integration(
#         path=Path("Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml")
#     ))
#     pack1.content_items.script.append(mock_script(
#         path=Path("Packs/SamplePack/Scripts/SampleScript/SampleScript.yml")
#     ))
#     pack2.content_items.script.append(mock_script(
#         "TestApiModule",
#         path=Path("Packs/SamplePack2/Scripts/TestApiModule/TestApiModule.yml")
#     ))
#     pack2.content_items.test_playbook.append(mock_test_playbook(
#         path=Path("Packs/SamplePack2/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml")
#     ))
#     pack3.content_items.script.append(mock_script(
#         "SampleScript2",
#         path=Path("Packs/SamplePac2k/Scripts/SampleScript2/SampleScript2.yml")
#     ))
#     repository.packs.extend([pack1, pack2, pack3])


# class TestGetRelationships:

#     def test_get_relationships(
#         self,
#         repository: ContentDTO,
#     ):
#         """
#         Given:
#             - A mocked model of a repository with a pack TestPack, containing two integrations
#               with the exact same properties but have different version ranges.
#         When:
#             - Running create_content_graph().
#         Then:
#             - Make sure the the integrations are not recognized as duplicates and the command succeeds.
#         """
#         create_mini_content(repository)
#         path = Path("Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml")
#         relationship = RelationshipType.USES
#         with ContentGraphInterface() as interface:
#             create_content_graph(interface)
#             resp = interface.get_relationships_by_path(
#                 path,
#                 relationship,
#                 1,
#             )
#             assert resp["object_id"] == "SampleIntegration"
#             assert True
