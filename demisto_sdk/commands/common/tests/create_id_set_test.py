import os
from collections import OrderedDict

from demisto_sdk.commands.common.update_id_set import ID_SET_ENTITIES
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


def test_create_id_set_flow(repo, mocker):
    # Note: if DEMISTO_SDK_ID_SET_REFRESH_INTERVAL is set it can fail the test
    mocker.patch.dict(os.environ, {'DEMISTO_SDK_ID_SET_REFRESH_INTERVAL': '-1'})
    number_of_packs_to_create = 10
    repo.setup_content_repo(number_of_packs_to_create)

    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path, print_logs=False)
        id_set_creator.create_id_set()

    id_set_content = repo.id_set.read_json_as_dict()
    assert not IsEqualFunctions.is_dicts_equal(id_set_content, {})
    assert IsEqualFunctions.is_lists_equal(list(id_set_content.keys()), ID_SET_ENTITIES + ['Packs'])
    for id_set_entity in ID_SET_ENTITIES:
        entity_content_in_id_set = id_set_content.get(id_set_entity)
        assert entity_content_in_id_set

        # Since Layouts folder contains both layouts and layoutcontainers then this folder has 2 * amount objects
        # And since there is a test playbook for each integration and script.
        if id_set_entity not in {'Layouts', 'TestPlaybooks'}:
            assert len(entity_content_in_id_set) == number_of_packs_to_create
        else:
            assert len(entity_content_in_id_set) == number_of_packs_to_create * 2


integration1 = {
    'Integration1': OrderedDict([('name', 'Integration1'), ('commands', ['test-command_1', 'test-command'])])}
integration2 = {
    'Integration2': OrderedDict([('name', 'Integration2'), ('commands', ['test-command', 'test-command_2'])])}
expected_output_map = {'test-command': ['Integration1', 'Integration2'],
                       'test-command_1': ['Integration1'],
                       'test-command_2': ['Integration2']}
playbook1 = {
    'Playbook1': OrderedDict(
        [('name', 'Playbook1'), ('command_to_integration', {'test-command': "", 'test-command_1': ""})])}
playbook2 = {
    'Playbook2': OrderedDict([('name', 'Playbook2'), ('command_to_integration', {'test-command': "",
                                                                                 'test-command_2': ""})])}


def test_create_command_to_implemented_integration_map(repo):
    """

    Given
        - a list of integrations

    When
        - create_command_to_implemented_integration_map is called

    Then
        - Validates that a dictionary between command name and list of all integration that implement this command
        was returned.

    """
    pack = repo.create_pack("Pack1")
    integration_list = [integration1, integration2]

    id_set_creator = IDSetCreator(pack.path, print_logs=False)
    id_set_creator.id_set["integrations"] = integration_list

    command_to_implemented_integration_map = id_set_creator.create_command_to_implemented_integration_map()
    assert command_to_implemented_integration_map == expected_output_map


def test_add_command_to_implementing_integrations_mapping(repo):
    """

    Given
        - an id_set file includes integrations and playbooks

    When
        - modify_id_set_command_to_integration_of_playbook is called

    Then
        - Validates that each command_to_integration in playbook is a dictionary between command name and list of all
        integration that implement this command.

    """
    pack = repo.create_pack("Pack1")
    integration_list = [integration1, integration2]
    playbook_list = [playbook1, playbook2]

    id_set_creator = IDSetCreator(pack.path, print_logs=False)
    id_set_creator.id_set["integrations"] = integration_list
    id_set_creator.id_set["playbooks"] = playbook_list

    id_set_creator.add_command_to_implementing_integrations_mapping()

    playbook_set = id_set_creator.id_set["playbooks"]
    assert playbook_set[0]["Playbook1"]['command_to_integration']['test-command'] == ['Integration1', 'Integration2']
    assert playbook_set[0]["Playbook1"]['command_to_integration']['test-command_1'] == ['Integration1']
    assert playbook_set[1]["Playbook2"]['command_to_integration']['test-command'] == ['Integration1', 'Integration2']
    assert playbook_set[1]["Playbook2"]['command_to_integration']['test-command_2'] == ['Integration2']
