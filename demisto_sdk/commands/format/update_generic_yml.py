import os
from typing import Dict, List, Optional

import click

from demisto_sdk.commands.common.constants import (ENTITY_TYPE_TO_DIR, INTEGRATION, NO_TESTS_DEPRECATED, PLAYBOOK,
                                                   TEST_PLAYBOOKS_DIR, FileType)
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.tools import (_get_file_id, find_type, get_entity_id_by_entity_type,
                                               get_not_registered_tests, get_scripts_and_commands_from_yml_data,
                                               get_yaml, is_uuid, listdir_fullpath)
from demisto_sdk.commands.format.update_generic import BaseUpdate

json = JSON_Handler()
yaml = YAML_Handler()


class BaseUpdateYML(BaseUpdate):
    """BaseUpdateYML is the base class for all yml updaters.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the id and version values.
    """
    ID_AND_VERSION_PATH_BY_YML_TYPE = {
        'IntegrationYMLFormat': 'commonfields',
        'ScriptYMLFormat': 'commonfields',
        'PlaybookYMLFormat': '',
        'TestPlaybookYMLFormat': '',
    }

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 assume_yes: bool = False,
                 deprecate: bool = False,
                 add_tests: bool = True,
                 interactive: bool = True,
                 clear_cache: bool = False):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, assume_yes=assume_yes, interactive=interactive, clear_cache=clear_cache)
        self.id_and_version_location = self.get_id_and_version_path_object()
        self.deprecate = deprecate
        self.add_tests = add_tests

    def _load_conf_file(self) -> Dict:
        """
        Loads the content of conf.json file from path 'CONF_PATH'
        Returns:
            The content of the json file
        """
        with open(CONF_PATH) as data_file:
            return json.load(data_file)

    def get_id_and_version_path_object(self):
        """Gets the dict that holds the id and version fields.
        Returns:
            Dict. Holds the id and version fields.
        """
        return self.get_id_and_version_for_data(self.data)

    def get_id_and_version_for_data(self, data):
        yml_type = self.__class__.__name__
        path = self.ID_AND_VERSION_PATH_BY_YML_TYPE[yml_type]
        return data.get(path, data)

    def update_id_to_equal_name(self) -> None:
        """Updates the id of the YML to be the same as it's name
            Only relevant for new files.
        """
        updated_integration_id = {}
        if not self.old_file:
            if self.verbose:
                click.echo('Updating YML ID to be the same as YML name')
            if is_uuid(self.id_and_version_location['id']):
                updated_integration_id[self.id_and_version_location['id']] = self.data['name']
            self.id_and_version_location['id'] = self.data['name']
        else:
            current_id = self.id_and_version_location.get('id')
            old_id = self.get_id_and_version_for_data(self.old_file).get('id')
            if current_id != old_id:
                click.secho(f'The modified YML file corresponding to the path: {self.relative_content_path} ID does not match the ID in remote YML file.'
                            f' Changing the YML ID from {current_id} back to {old_id}.')
                self.id_and_version_location['id'] = old_id
        if updated_integration_id:
            self.updated_ids.update(updated_integration_id)

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        if self.source_file != self.output_file and self.verbose:
            click.secho(f'Saving output YML file to {self.output_file} \n', fg='white')
        with open(self.output_file, 'w') as f:
            yaml.dump(self.data, f)  # ruamel preservers multilines

    def copy_tests_from_old_file(self):
        """Copy the tests key from old file if exists.
        """
        if self.old_file:
            if not self.data.get('tests', '') and self.old_file.get('tests', ''):
                self.data['tests'] = self.old_file['tests']

    def update_yml(self, default_from_version: Optional[str] = '', file_type: str = '') -> None:
        """Manager function for the generic YML updates."""

        self.set_fromVersion(default_from_version=default_from_version, file_type=file_type)
        self.remove_copy_and_dev_suffixes_from_name()
        self.remove_unnecessary_keys()
        self.remove_spaces_end_of_id_and_name()
        self.update_id_to_equal_name()
        self.set_version_to_default(self.id_and_version_location)
        self.copy_tests_from_old_file()
        if self.deprecate:
            self.update_deprecate(file_type=file_type)
        self.sync_data_to_master()

    def update_tests(self) -> None:
        """
        If there are no tests configured: Prompts a question to the cli that asks the user whether he wants to add
        'No tests' under 'tests' key or not and format the file according to the answer
        """
        if not self.data.get('tests', ''):
            # try to get the test playbook files from the TestPlaybooks dir in the pack
            pack_path = os.path.dirname(os.path.dirname(os.path.abspath(self.source_file)))
            test_playbook_dir_path = os.path.join(pack_path, TEST_PLAYBOOKS_DIR)
            test_playbook_ids = []
            file_entity_type = find_type(self.source_file, _dict=self.data, file_type='yml')
            file_id = get_entity_id_by_entity_type(self.data, ENTITY_TYPE_TO_DIR.get(file_entity_type.value, ""))
            commands, scripts = get_scripts_and_commands_from_yml_data(self.data, file_entity_type)
            commands_names = [command.get('id') for command in commands]
            try:
                # Collecting the test playbooks
                test_playbooks_files = [tpb_file for tpb_file in listdir_fullpath(test_playbook_dir_path) if
                                        find_type(tpb_file) == FileType.TEST_PLAYBOOK]
                for tpb_file_path in test_playbooks_files:  # iterate over the test playbooks in the dir
                    test_playbook_data = get_yaml(tpb_file_path)
                    test_playbook_id = get_entity_id_by_entity_type(test_playbook_data,
                                                                    content_entity='')
                    if not scripts and not commands:  # Better safe than sorry
                        test_playbook_ids.append(test_playbook_id)
                    else:
                        added = False
                        tpb_commands, tpb_scripts = get_scripts_and_commands_from_yml_data(
                            test_playbook_data, FileType.TEST_PLAYBOOK)

                        for tpb_command in tpb_commands:
                            tpb_command_name = tpb_command.get('id')
                            tpb_command_source = tpb_command.get('source', '')
                            if tpb_command_source and file_id and file_id != tpb_command_source:
                                continue

                            if not added and tpb_command_name in commands_names:
                                command_source = commands[commands_names.index(tpb_command_name)].get('source', '')
                                if command_source == tpb_command_source or command_source == '':
                                    test_playbook_ids.append(test_playbook_id)
                                    added = True
                                    break

                        if not added:
                            for tpb_script in tpb_scripts:
                                if tpb_script in scripts:
                                    test_playbook_ids.append(test_playbook_id)
                                    break

                self.data['tests'] = test_playbook_ids
            except FileNotFoundError:
                pass

            if not test_playbook_ids:
                # In case no_interactive flag was given - modify the tests without confirmation
                if self.assume_yes or not self.add_tests:
                    should_modify_yml_tests = True
                else:
                    should_modify_yml_tests = click.confirm(f'The file {self.source_file} has no test playbooks '
                                                            f'configured. Do you want to configure it with "No tests"?')
                if should_modify_yml_tests:
                    click.echo(f'Formatting {self.output_file} with "No tests"')
                    self.data['tests'] = ['No tests (auto formatted)']

    def update_conf_json(self, file_type: str) -> None:
        """
        Updates conf.json with the file's test playbooks if not registered already according to user's answer
        to the prompt message
        Args:
            file_type: The typr of the file, can be integration, playbook or script
        """
        test_playbooks = self.data.get('tests', [])
        if not test_playbooks:
            return
        no_test_playbooks_explicitly = any(test for test in test_playbooks if 'no test' in test.lower())
        if no_test_playbooks_explicitly:
            return
        try:
            conf_json_content = self._load_conf_file()
        except FileNotFoundError:
            if self.verbose:
                click.secho(f'Unable to find {CONF_PATH} - skipping update.', fg='yellow')
            return
        conf_json_test_configuration = conf_json_content['tests']
        content_item_id = _get_file_id(file_type, self.data)
        not_registered_tests = get_not_registered_tests(conf_json_test_configuration,
                                                        content_item_id,
                                                        file_type,
                                                        test_playbooks)
        if not_registered_tests:
            not_registered_tests_string = '\n'.join(not_registered_tests)
            if self.assume_yes:
                should_edit_conf_json = True
            else:
                should_edit_conf_json = click.confirm(f'The following test playbooks are not configured in conf.json file '
                                                      f'{not_registered_tests_string}\n'
                                                      f'Would you like to add them now?')
            if should_edit_conf_json:
                conf_json_content['tests'].extend(self.get_test_playbooks_configuration(not_registered_tests,
                                                                                        content_item_id,
                                                                                        file_type))
                self._save_to_conf_json(conf_json_content)
                click.echo('Added test playbooks to conf.json successfully')
            else:
                click.echo('Skipping test playbooks configuration')

    def _save_to_conf_json(self, conf_json_content: Dict) -> None:
        """Save formatted JSON data to destination file."""
        with open(CONF_PATH, 'w') as file:
            json.dump(conf_json_content, file, indent=4)

    def update_deprecate(self, file_type=None):
        """
        Update the yaml file as deprecated.

        Args:
            file_type: The type of the yml file.
        """

        self.data['deprecated'] = True
        self.data['tests'] = [NO_TESTS_DEPRECATED]

        if file_type in [INTEGRATION, PLAYBOOK]:

            description_field = 'description'

            if file_type == INTEGRATION:
                if 'display' in self.data and not self.data['display'].endswith('(Deprecated)'):
                    self.data['display'] = f'{self.data["display"]} (Deprecated)'

                for command in self.data.get('script', {}).get('commands', []):
                    command['deprecated'] = True

        else:
            description_field = 'comment'

        user_response = input("\nPlease enter the replacement entity display name if any and press Enter if not.\n")

        if user_response:
            self.data[description_field] = f'Deprecated. Use {user_response} instead.'

        else:
            self.data[description_field] = 'Deprecated. No available replacement.'

    @staticmethod
    def get_test_playbooks_configuration(test_playbooks: List, content_item_id: str, file_type: str) -> List[Dict]:
        """
        Gets the content item playbook's configuration in order to add it to conf.json
        Args:
            test_playbooks: Test Playbooks IDs
            content_item_id: Content item's ID
            file_type: The type of the file, can be playbook, integration or script

        Returns:

        """
        if file_type == 'integration':
            return [{'integrations': content_item_id, 'playbookID': test_playbook_id} for test_playbook_id in
                    test_playbooks]
        elif file_type in {'playbook', 'script'}:
            return [{'playbookID': test_playbook_id} for test_playbook_id in test_playbooks]
        return []

    def remove_spaces_end_of_id_and_name(self):
        """Updates the id and name of the YML to have no spaces on its end
        """
        if not self.old_file:
            if self.verbose:
                click.echo('Updating YML ID and name to be without spaces at the end')
            self.data['name'] = self.data['name'].strip()
            self.id_and_version_location['id'] = self.id_and_version_location['id'].strip()
