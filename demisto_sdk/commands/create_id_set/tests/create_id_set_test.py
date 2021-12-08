import json
import os
import shutil
from collections import OrderedDict
from tempfile import mkdtemp

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions
import demisto_sdk.commands.common.update_id_set as uis
import demisto_sdk.commands.create_id_set.create_id_set as cis

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'


class TestIDSetCreator:
    def setup(self):
        self.id_set_full_path = os.path.join(TESTS_DIR, 'test_files', 'content_repo_example', 'id_set.json')
        self._test_dir = mkdtemp()
        self.file_path = os.path.join(self._test_dir, 'id_set.json')

    def teardown(self):
        # delete the id set file
        try:
            if os.path.isfile(self.file_path) or os.path.islink(self.file_path):
                os.unlink(self.file_path)
            elif os.path.isdir(self.file_path):
                shutil.rmtree(self.file_path)
        except Exception as err:
            print(f'Failed to delete {self.file_path}. Reason: {err}')

    def test_create_id_set_output(self):
        id_set_creator = IDSetCreator(self.file_path)

        id_set_creator.create_id_set()
        assert os.path.exists(self.file_path)

    def test_create_id_set_on_specific_pack_output(self):
        """
        Given
        - input - specific pack to create from it ID set
        - output - path to return the created ID set

        When
        - create ID set on this pack

        Then
        - ensure that the created ID set is in the path of the output

        """
        id_set_creator = IDSetCreator(self.file_path, input='Packs/AMP')

        id_set_creator.create_id_set()
        assert os.path.exists(self.file_path)

    def test_create_id_set_no_output(self, mocker):
        mocker.patch.object(uis, 'cpu_count', return_value=1)
        id_set_creator = IDSetCreator(output=None)

        id_set = id_set_creator.create_id_set()
        assert not os.path.exists(self.file_path)
        assert id_set is not None
        assert 'scripts' in id_set.keys()
        assert 'integrations' in id_set.keys()
        assert 'playbooks' in id_set.keys()
        assert 'TestPlaybooks' in id_set.keys()
        assert 'Classifiers' in id_set.keys()
        assert 'Dashboards' in id_set.keys()
        assert 'IncidentFields' in id_set.keys()
        assert 'IncidentTypes' in id_set.keys()
        assert 'IndicatorFields' in id_set.keys()
        assert 'IndicatorTypes' in id_set.keys()
        assert 'Layouts' in id_set.keys()
        assert 'Reports' in id_set.keys()
        assert 'Widgets' in id_set.keys()
        assert 'Mappers' in id_set.keys()
        assert 'Packs' in id_set.keys()

    def test_create_id_set_on_specific_pack(self, mocker, repo):
        """
        Given
        - two packs with integrations to create an ID set from

        When
        - create ID set on one of the packs

        Then
        - ensure there is only one integration in the ID set integrations list
        - ensure output id_set contains only the pack on which created the ID set on
        - ensure output id_set does not contain the second pack

        """
        import demisto_sdk.commands.common.update_id_set as u
        mocker.patch.object(u, 're_create_id_set', return_value={})
        #mocker.patch('demisto_sdk.commands.common.update_id_set', return_value={})
        packs = repo.packs

        pack_to_create_id_set_on = repo.create_pack('pack_to_create_id_set_on')
        pack_to_create_id_set_on.create_integration(yml={'commonfields': {'id': 'id1'}, 'category': '', 'name':
            'integration to create id set', 'script': {'type': 'python'}},
                                                    name='integration1')
        packs.append(pack_to_create_id_set_on)

        pack_to_not_create_id_set_on = repo.create_pack('pack_to_not_create_id_set_on')
        pack_to_not_create_id_set_on.create_integration(yml={'commonfields': {'id2': 'id'}, 'category': '', 'name':
            'integration to not create id set'}, name='integration2')
        packs.append(pack_to_not_create_id_set_on)

        id_set_creator = IDSetCreator(self.file_path, pack_to_create_id_set_on.path)

        id_set_creator.create_id_set()

        with open(self.file_path, 'r') as id_set_file:
            private_id_set = json.load(id_set_file)

        assert len(private_id_set['integrations']) == 1
        assert private_id_set['integrations'][0].get('id1', {}).get('name', '') == 'integration to create id set'
        assert private_id_set['integrations'][0].get('id2', {}).get('name', '') == ''

    def test_create_id_set_on_specific_empty_pack(self, repo):
        """
        Given
        - an empty pack to create from it ID set

        When
        - create ID set on this pack

        Then
        - ensure that an ID set is created and no error is returned
        - ensure output id_set is empty

        """
        pack = repo.create_pack()

        id_set_creator = IDSetCreator(self.file_path, pack.path)

        id_set_creator.create_id_set()

        with open(self.file_path, 'r') as id_set_file:
            private_id_set = json.load(id_set_file)
        for content_entity, content_entity_value_list in private_id_set.items():
            if content_entity != 'Packs':
                assert len(content_entity_value_list) == 0
            else:
                assert len(content_entity_value_list) == 1


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
    assert IsEqualFunctions.is_lists_equal(list(id_set_content.keys()), uis.ID_SET_ENTITIES + ['Packs'])
    for id_set_entity in uis.ID_SET_ENTITIES:
        entity_content_in_id_set = id_set_content.get(id_set_entity)
        assert entity_content_in_id_set, f'ID set for {id_set_entity} is empty'

        factor = 1
        if id_set_entity in {'Layouts', 'TestPlaybooks', 'Jobs'}:
            '''
            Layouts: The folder contains both layouts and layoutcontainers
            TestPlaybooks: each integration and script has a test playbook
            Jobs: The default test suite pack has two jobs (is_feed=true, is_feed=false), and a playbook
            '''
            factor = 2

        elif id_set_entity == 'playbooks':
            '''
            One playbook is generated for every pack,
            And one more is created for each of the 2 Job objects that are automatically created in every pack.
            '''
            factor = 3

        assert len(entity_content_in_id_set) == factor * number_of_packs_to_create


def setup_id_set():
    integration1 = {
        'Integration1': OrderedDict([('name', 'Integration1'), ('commands', ['test-command_1', 'test-command'])])}
    integration2 = {
        'Integration2': OrderedDict([('name', 'Integration2'), ('commands', ['test-command', 'test-command_2'])])}

    playbook1 = {
        'Playbook1': OrderedDict(
            [('name', 'Playbook1'), ('command_to_integration', {'test-command': "", 'test-command_1': ""})])}
    playbook2 = {
        'Playbook2': OrderedDict([('name', 'Playbook2'), ('command_to_integration', {'test-command': "",
                                                                                     'test-command_2': ""})])}

    id_set_creator = IDSetCreator(print_logs=False)
    id_set_creator.id_set["integrations"] = [integration1, integration2]
    id_set_creator.id_set["playbooks"] = [playbook1, playbook2]

    return id_set_creator


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
    expected_output_map = {'test-command': ['Integration1', 'Integration2'],
                           'test-command_1': ['Integration1'],
                           'test-command_2': ['Integration2']}
    id_set_creator = setup_id_set()

    command_to_implemented_integration_map = id_set_creator.create_command_to_implemented_integration_map()
    assert command_to_implemented_integration_map == expected_output_map


class TestAddCommandToImplementingIntegrationsMapping:
    @staticmethod
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
        id_set_creator = setup_id_set()

        id_set_creator.add_command_to_implementing_integrations_mapping()

        playbook_set = id_set_creator.id_set["playbooks"]
        assert playbook_set[0]["Playbook1"]['command_to_integration']['test-command'] == ['Integration1',
                                                                                          'Integration2']
        assert playbook_set[0]["Playbook1"]['command_to_integration']['test-command_1'] == ['Integration1']
        assert playbook_set[1]["Playbook2"]['command_to_integration']['test-command'] == ['Integration1',
                                                                                          'Integration2']
        assert playbook_set[1]["Playbook2"]['command_to_integration']['test-command_2'] == ['Integration2']

    @staticmethod
    def test_do_not_modify_specific_brand(repo):
        """
        Given
        - playbook with a command using a specific brand
        - playbook with a command using a specific brand

        When
        - updating the commands_to_integrations fields in playbooks

        Then
        - only update commands that don't have a specific brand

        """
        integrations = [
            {
                'MainInteg': OrderedDict([
                    ('name', 'MainInteg'),
                    ('commands', ['generic-command']),
                ])
            },
            {
                'SecondaryInteg': OrderedDict([
                    ('name', 'SecondaryInteg'),
                    ('commands', ['generic-command', 'specific-command']),
                ])
            },
        ]
        playbooks = [
            {
                'Playbook1': OrderedDict([
                    ('name', 'Playbook1'),
                    ('command_to_integration', {
                        'specific-command': "",
                        'generic-command': "",
                    }),
                ]),
            },
            {
                'Playbook2': OrderedDict([
                    ('name', 'Playbook2'),
                    ('command_to_integration', {
                        'generic-command': 'MainInteg',
                        'no-integration': '',
                    }),
                ]),
            },
        ]

        id_set_creator = IDSetCreator(print_logs=False)
        id_set_creator.id_set["integrations"] = integrations
        id_set_creator.id_set["playbooks"] = playbooks

        id_set_creator.add_command_to_implementing_integrations_mapping()

        playbook1 = id_set_creator.id_set['playbooks'][0]['Playbook1']
        playbook2 = id_set_creator.id_set['playbooks'][1]['Playbook2']
        assert playbook1['command_to_integration']['specific-command'] == ['SecondaryInteg']
        assert playbook1['command_to_integration']['generic-command'] == ['MainInteg', 'SecondaryInteg']
        assert playbook2['command_to_integration']['generic-command'] == 'MainInteg'
        assert playbook2['command_to_integration']['no-integration'] == ''

    @staticmethod
    def test_generic_command_that_does_not_use_a_specific_brand(repo):
        """
        Given
        - A playbook with a generic command (send-notification, etc.) that does not use a specific brand

        When
        - Updating the commands_to_integrations fields in playbooks

        Then
        - Do not update 'command_to_integration' fields with any other brands

        """
        integrations = [
            {
                'Slack': OrderedDict([
                    ('name', 'Slack'),
                    ('commands', ['send-notification']),
                ])
            },
            {
                'Syslog': OrderedDict([
                    ('name', 'Syslog'),
                    ('commands', ['send-notification']),
                ])
            },
        ]
        playbooks = [
            {
                'Playbook': OrderedDict([
                    ('name', 'Playbook'),
                    ('command_to_integration', {
                        'send-notification': '',
                    }),
                ]),
            }
        ]

        id_set_creator = IDSetCreator(print_logs=False)
        id_set_creator.id_set["integrations"] = integrations
        id_set_creator.id_set["playbooks"] = playbooks

        id_set_creator.add_command_to_implementing_integrations_mapping()

        playbook = id_set_creator.id_set['playbooks'][0]['Playbook']
        assert playbook['command_to_integration']['send-notification'] == ''

    @staticmethod
    def test_generic_command_that_uses_a_specific_brand(repo):
        """
        Given
        - A playbook with a generic command (send-notification, etc.) that uses a specific brand

        When
        - Updating the commands_to_integrations fields in playbooks

        Then
        - Do not update 'command_to_integration' fields with any other brands

        """
        integrations = [
            {
                'Slack': OrderedDict([
                    ('name', 'Slack'),
                    ('commands', ['send-notification']),
                ])
            },
            {
                'Syslog': OrderedDict([
                    ('name', 'Syslog'),
                    ('commands', ['send-notification']),
                ])
            },
        ]
        playbooks = [
            {
                'Playbook': OrderedDict([
                    ('name', 'Playbook'),
                    ('command_to_integration', {
                        'send-notification': 'Slack',
                    }),
                ]),
            }
        ]

        id_set_creator = IDSetCreator(print_logs=False)
        id_set_creator.id_set["integrations"] = integrations
        id_set_creator.id_set["playbooks"] = playbooks

        id_set_creator.add_command_to_implementing_integrations_mapping()

        playbook = id_set_creator.id_set['playbooks'][0]['Playbook']
        assert playbook['command_to_integration']['send-notification'] == 'Slack'
