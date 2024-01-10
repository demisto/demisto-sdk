from pathlib import Path
from zipfile import ZipFile

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


def create_mini_content(graph_repo : Repo):
    """
    Create the following content in the repo
    - A pack SamplePack, containing:
        - An integration SampleIntegration, which:
            1. Has a single command test-command.
            2. Imports TestApiModule in the code.
            3. Is tested by SampleTestPlaybook which defined in pack SamplePack2.
            4. A default classifier SampleClassifier which defined in pack SamplePack2.
        - A script SampleScript that uses SampleScript2.
    - A pack SamplePack2, containing:
        1. A script TestApiModule that uses SampleScript2 which defined in pack SamplePack2.
        2. A classifier SampleClassifier.
        3. A test playbook SampleTestPlaybook.
    - A pack SamplePack3, containing:
        1. A script SampleScript2

    Args:
        graph_repo (Repo): the repo to work with
    """
    sample_pack = graph_repo.create_pack('SamplePack')
    sample_pack.create_script(
        'SampleScript',
        code='demisto.execute_command("SampleScriptTwo", dArgs)'
    )
    integration = sample_pack.create_integration(
        name='SampleIntegration',
        code='from TestApiModule import *'
    )
    integration.set_commands(['test-command'])
    integration.set_data(tests=['SampleTestPlaybook'], defaultclassifier='SampleClassifier')
    
    
    sample_pack_2 = graph_repo.create_pack('SamplePack2')
    sample_pack_2.create_script('TestApiModule', code='demisto.execute_command("SampleScriptTwo", dArgs)')
    sample_pack_2.create_test_playbook('SampleTestPlaybook')
    sample_pack_2.create_classifier('SampleClassifier')
    
    sample_pack_3 = graph_repo.create_pack('SamplePack3')
    sample_pack_3.create_script('SampleScriptTwo')

class TestCreateContentGraph:
    def test_create_content_graph_end_to_end(self, graph_repo: Repo, tmp_path: Path, mocker):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph()
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        repo = graph_repo
        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )
        mocker.patch.object(
            PackMetadata, "_get_tags_from_landing_page", retrun_value={}
        )

        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        integration = pack.create_integration()
        integration.create_default_integration(
            "TestIntegration", ["test-command1", "test-command2"]
        )
        script = pack.create_script()
        api_module = pack.create_script()
        script.create_default_script("SampleScript")
        api_module.create_default_script("TestApiModule")

        pack.create_classifier(
            name="SampleClassifier", content=load_json("classifier.json")
        )

        interface = repo.create_graph(output_path=tmp_path)
        packs = interface.search(
            marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK
        )
        integrations = interface.search(
            marketplace=MarketplaceVersions.XSOAR,
            content_type=ContentType.INTEGRATION,
        )
        all_content_items = interface.search(marketplace=MarketplaceVersions.XSOAR)
        content_cto = interface.marshal_graph(MarketplaceVersions.XSOAR)
        assert len(packs) == 1
        assert len(integrations) == 1
        assert len(all_content_items) == 8
        returned_pack = packs[0]
        assert returned_pack.object_id == "TestPack"
        # make sure that data from pack_metadata.json updated
        assert returned_pack.name == "HelloWorld"
        assert returned_pack.support == "community"
        assert len(packs[0].content_items.integration) == 1
        returned_integration = integration.get_graph_object(interface)
        assert returned_integration == integrations[0]
        assert returned_integration.name == "TestIntegration"
        assert {command.name for command in returned_integration.commands} == {
            "test-command",
            "test-command1",
            "test-command2",
        }
        returned_scripts = {
            script.object_id for script in packs[0].content_items.script
        }
        assert returned_scripts == {"SampleScript", "TestApiModule"}
        with ChangeCWD(repo.path):
            content_cto.dump(tmp_path, MarketplaceVersions.XSOAR, zip=False)
        assert (tmp_path / "TestPack").exists()
        assert (tmp_path / "TestPack" / "metadata.json").exists()
        assert (
            tmp_path / "TestPack" / "Integrations" / "integration-integration_0.yml"
        ).exists()
        assert (tmp_path / "TestPack" / "Scripts" / "script-script0.yml").exists()
        assert (tmp_path / "TestPack" / "Scripts" / "script-script1.yml").exists()

        # make sure that the output file zip is created
        assert Path.exists(tmp_path / "xsoar.zip")
        with ZipFile(tmp_path / "xsoar.zip", "r") as zip_obj:
            zip_obj.extractall(tmp_path / "extracted")
            # make sure that the extracted files are all .csv
            extracted_files = list(tmp_path.glob("extracted/*"))
            assert extracted_files
            assert all(
                file.suffix == ".graphml" or file.name == "metadata.json"
                for file in extracted_files
            )

    def test_create_content_graph_relationships(
        self,
        graph_repo: Repo
    ):
        """
        Given:
            - A repo contain content structure defined in create_mini_content
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph has all the corresponding nodes and relationships.
        """
        create_mini_content(graph_repo)

        interface = graph_repo.create_graph()
        
        sample_pack = graph_repo.packs[0]
        sample_pack_graph_obj = sample_pack.get_graph_object(interface)
        sample_pack_2_graph_obj = graph_repo.packs[1].get_graph_object(interface)
        sample_pack_3_graph_obj = graph_repo.packs[2].get_graph_object(interface)
        
        integration_graph_obj = sample_pack.integrations[0].get_graph_object(interface)
        sample_pack_script_graph_obj = sample_pack.scripts[0].get_graph_object(interface)
        # assert sample_pack depends on sample_pack_2 and sample_pack_3
        for rel_type, relations in sample_pack_graph_obj.relationships_data.items():
            for r in relations:
                if rel_type == RelationshipType.DEPENDS_ON:
                    assert r.content_item_to in [sample_pack_2_graph_obj, sample_pack_3_graph_obj]
                elif rel_type == RelationshipType.IN_PACK:
                    assert r.content_item_to in [
                        integration_graph_obj,
                        sample_pack_script_graph_obj
                    ]
                else:
                    assert False
        
        # assert integration relationships
        rel_map = {
            RelationshipType.USES: sample_pack_2_graph_obj.content_items.classifier[0],
            RelationshipType.TESTED_BY: sample_pack_2_graph_obj.content_items.test_playbook[0],
            RelationshipType.IMPORTS: sample_pack_2_graph_obj.content_items.script[0],
            RelationshipType.IN_PACK: sample_pack_graph_obj,
        }
        for rel_type, rel_to_obj in rel_map.items():
            content_item_to = next(iter(integration_graph_obj.relationships_data[rel_type])).content_item_to
            assert content_item_to == rel_to_obj or content_item_to.not_in_repository

    def test_create_content_graph_two_integrations_with_same_command(
        self,
        graph_repo: Repo,
    ):
        """
        Given:
            - A repo with pack, containing two integrations,
              each has a command named test-command.
        When:
            - Running create_content_graph().
        Then:
            - Make sure only one command node was created.
        """
        pack = graph_repo.create_pack()
        pack.create_integration('SampleIntegration1').set_commands(['test-command'])
        pack.create_integration('SampleIntegration2').set_commands(['test-command'])
        
        interface = graph_repo.create_graph()
        
        assert pack.integrations[0].get_graph_object(interface).object_id == "SampleIntegration1"
        assert pack.integrations[1].get_graph_object(interface).object_id == "SampleIntegration2"
        assert len(interface.search(MarketplaceVersions.XSOAR, content_type=ContentType.COMMAND)) == 1
  
    def test_create_content_graph_playbook_uses_script_not_in_repository(self, graph_repo: Repo):
        pack = graph_repo.create_pack()
        pack.create_playbook().add_default_task(task_script_name='NotExistingScript')
        
        interface = graph_repo.create_graph()
        script = interface.search(object_id="NotExistingScript")[0]
        
        assert script.not_in_repository
  
    def test_create_content_graph_duplicate_widgets(
        self,
        graph_repo: Repo
    ):
        """
        Given:
            - A repository with a pack TestPack, containing two widgets
              with the exact same id, fromversion and marketplaces properties.
        When:
            - Running create_content_graph().
        Then:
            - Make sure both widgets exist in the graph.
        """
        pack = graph_repo.create_pack()
        
        widget1 = pack.create_widget().object
        widget2 = pack.create_widget().object
        
        widget1.object_id = widget2.object_id = 'SampleWidget'

        widget1.save()
        widget2.save()
        
        interface = graph_repo.create_graph()
        
        assert len(interface.search(object_id="SampleWidget")) == 2

    def test_create_content_graph_duplicate_integrations_different_marketplaces(self, graph_repo: Repo):
        pack = graph_repo.create_pack()
        pack.create_integration().set_data(**{'commonfields.id': 'SampleIntegration', 'marketplaces':[MarketplaceVersions.XSOAR.value]})
        pack.create_integration().set_data(**{'commonfields.id': 'SampleIntegration', 'marketplaces':[MarketplaceVersions.MarketplaceV2.value]})
        
        interface = graph_repo.create_graph()
        
        assert len(interface.search(object_id='SampleIntegration')) == 2
        assert len(interface.search(MarketplaceVersions.XSOAR, object_id='SampleIntegration')) == 1
        assert len(interface.search(MarketplaceVersions.MarketplaceV2, object_id='SampleIntegration')) == 1
         
    def test_create_content_graph_duplicate_integrations_different_fromversion(
        self,
        graph_repo: Repo,
    ):
        """
        Given:
            - A repository with a pack, containing two integrations
              with the exact same properties but have different version ranges.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the integrations are not recognized as duplicates and the command succeeds.
        """
        pack = graph_repo.create_pack()
        
        pack.create_integration().set_data(**{'commonfields.id': 'SampleIntegration', 'toversion':'6.0.0'})
        pack.create_integration().set_data(**{'commonfields.id': 'SampleIntegration', 'toversion':'6.0.2'})
        
        interface = graph_repo.create_graph()
        
        assert len(interface.search(object_id="SampleIntegration")) == 2

    def test_create_content_graph_empty_repository(
        self,
        graph_repo: Repo
    ):
        """
        Given:
            - An empty repository.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph are empty.
        """
        interface = graph_repo.create_graph()
        assert not interface.search()

    def test_create_content_graph_incident_to_alert_scripts(
        self, graph_repo: Repo, tmp_path: Path
    ):
        """
        Given:
            - A pack, containing two scripts,
            one (getIncident) is set with skipping the preparation of incident to alert
            and the other (setIncident) is not.
        When:
            - Running create_content_graph().
        Then:
            - Ensure that `getIncident` script has passed the prepare process as expected.
            - Ensure the 'setIncident' script has not passed incident to alert preparation.
        """
        pack = graph_repo.create_pack()
        pack.create_script(name="getIncident")
        pack.create_script(name="setIncident", skip_prepare=[SKIP_PREPARE_SCRIPT_NAME])

        interface = graph_repo.create_graph(output_path=tmp_path)
        packs = interface.search(
            marketplace=MarketplaceVersions.MarketplaceV2,
            content_type=ContentType.PACK,
        )
        scripts = interface.search(
            marketplace=MarketplaceVersions.MarketplaceV2,
            content_type=ContentType.SCRIPT,
        )
        all_content_items = interface.search(
            marketplace=MarketplaceVersions.MarketplaceV2
        )
        content_cto = interface.marshal_graph(MarketplaceVersions.MarketplaceV2)

        assert len(packs) == 1
        assert len(scripts) == 2
        assert len(all_content_items) == 3
        
        with ChangeCWD(graph_repo.path):
            content_cto.dump(tmp_path, MarketplaceVersions.MarketplaceV2, zip=False)
        scripts_path = tmp_path / pack.name / 'Scripts'
        assert (scripts_path / "script-getIncident.yml").exists()
        assert (scripts_path / "script-getAlert.yml").exists()
        assert (scripts_path / "script-setIncident.yml").exists()
        assert not (scripts_path / "script-setAlert.yml").exists()

    def test_create_content_graph_relationships_from_metadata(
        self,
        graph_repo: Repo,
    ):
        """
        Given:
            - A pack Core, which depends on NonCorePack according to the pack metadata
        When:
            - Running create_content_graph().
        Then:
            - Make sure the relationship's is_test is not null.
        """
        graph_repo.create_pack("NonCorePack")
        graph_repo.create_pack("Core").set_data(
            dependencies={"NonCorePack": {"mandatory": True, "display_name": "Non Core Pack"}}
        )
        
        interface = graph_repo.create_graph()
        
        where_test_null = 'WHERE r.is_test IS NULL'
        query = "MATCH p=()-[r:DEPENDS_ON]->() {where} RETURN p"
        data = interface.run_single_query(query.format(where=''))[0]['p']
        empty_data = interface.run_single_query(query.format(where=where_test_null))
        
        assert data[0]['object_id'] == 'Core'
        assert data[1] == 'DEPENDS_ON'
        assert data[2]['object_id'] == 'NonCorePack'
        assert not empty_data

    # @pytest.mark.parametrize(
    #     "docker_image, expected_python_version, is_taken_from_dockerhub",
    #     [
    #         ("demisto/python3:3.10.11.54799", "3.10.11", False),
    #         ("demisto/pan-os-python:1.0.0.68955", "3.10.12", True),
    #     ],
    # )
    # def test_create_content_graph_with_python_version(
    #     self,
    #     mocker,
    #     graph_repo: Repo,
    #     docker_image: str,
    #     expected_python_version: str,
    #     is_taken_from_dockerhub: bool,
    # ):
    #     """
    #     Given:
    #         Case A: docker image that its python version exists in the dockerfiles metadata file
    #         Case B: docker image that its python version does not exist in the dockerfiles metadata file

    #     When:
    #         - Running create_content_graph()

    #     Then:
    #         - make sure that in both cases the python_version (lazy property) was loaded into the Integration
    #           model because we want it in the graph metadata
    #         Case A: the python version was taken from the dockerfiles metadata file
    #         Case B: the python version was taken from the dockerhub api
    #     """
    #     from packaging.version import Version

    #     dockerhub_api_mocker = mocker.patch(
    #         "demisto_sdk.commands.common.docker_helper._get_python_version_from_dockerhub_api",
    #         return_value=Version(expected_python_version),
    #     )

    #     pack = graph_repo.create_pack()
    #     pack.create_integration(docker_image=docker_image)
    #     mocker.patch.object(PackParser, "parse_ignored_errors", return_value={})

    #     interface = graph_repo.create_graph()
    #     integrations = interface.search(
    #         marketplace=MarketplaceVersions.XSOAR,
    #         content_type=ContentType.INTEGRATION,
    #     )
    #     assert expected_python_version == integrations[0].to_dict()["python_version"]
    #     assert dockerhub_api_mocker.called == is_taken_from_dockerhub
