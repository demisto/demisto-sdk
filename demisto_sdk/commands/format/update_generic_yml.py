import json
from typing import Dict, List

import click
from demisto_sdk.commands.common.tools import (LOG_COLORS, _get_file_id,
                                               get_not_registered_tests,
                                               print_color)
from demisto_sdk.commands.format.update_generic import BaseUpdate
from ruamel.yaml import YAML

ryaml = YAML()
ryaml.allow_duplicate_keys = True
ryaml.preserve_quotes = True  # type: ignore


class BaseUpdateYML(BaseUpdate):
    """BaseUpdateYML is the base class for all yml updaters.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """
    ID_AND_VERSION_PATH_BY_YML_TYPE = {
        'IntegrationYMLFormat': 'commonfields',
        'ScriptYMLFormat': 'commonfields',
        'PlaybookYMLFormat': '',
    }
    CONF_PATH = "./Tests/conf.json"

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate)
        self.id_and_version_location = self.get_id_and_version_path_object()

    def _load_conf_file(self) -> Dict:
        """
        Loads the content of conf.json file from path 'CONF_PATH'
        Returns:
            The content of the json file
        """
        with open(self.CONF_PATH) as data_file:
            return json.load(data_file)

    def get_id_and_version_path_object(self):
        """Gets the dict that holds the id and version fields.
        Returns:
            Dict. Holds the id and version fields.
        """
        yml_type = self.__class__.__name__
        path = self.ID_AND_VERSION_PATH_BY_YML_TYPE[yml_type]
        return self.data.get(path, self.data)

    def update_id_to_equal_name(self):
        """Updates the id of the YML to be the same as it's name."""
        print('Updating YML ID to be the same as YML name')
        self.id_and_version_location['id'] = self.data['name']

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        print(F'Saving output YML file to {self.output_file}')
        with open(self.output_file, 'w') as f:
            ryaml.dump(self.data, f)  # ruamel preservers multilines

    def copy_tests_from_old_file(self):
        """Copy the tests key from old file if exists.
        """
        if self.old_file:
            if not self.data.get('tests', '') and self.old_file.get('tests', ''):
                self.data['tests'] = self.old_file['tests']

    def update_yml(self):
        """Manager function for the generic YML updates."""
        print_color(F'=======Starting updates for file: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.set_fromVersion(self.from_version)
        self.remove_copy_and_dev_suffixes_from_name()
        self.remove_unnecessary_keys()
        self.update_id_to_equal_name()
        self.set_version_to_default(self.id_and_version_location)
        self.copy_tests_from_old_file()

        print_color(F'=======Finished updates for file: {self.output_file}=======', LOG_COLORS.YELLOW)

    def update_tests(self) -> None:
        """
        If there are no tests configured: Prompts a question to the cli that asks the user whether he wants to add
        'No tests' under 'tests' key or not and format the file according to the answer
        """
        # No need to add test playbooks for test playbooks
        if 'TestPlaybooks' in self.source_file:
            return
        if not self.data.get('tests', ''):
            should_modify_yml_tests = click.confirm(f'The file {self.source_file} has no test playbooks configured. '
                                                    f'Do you want to configure it with "No tests"?')
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
        conf_json_content = self._load_conf_file()
        conf_json_test_configuration = conf_json_content['tests']
        content_item_id = _get_file_id(file_type, self.data)
        not_registered_tests = get_not_registered_tests(conf_json_test_configuration,
                                                        content_item_id,
                                                        file_type,
                                                        test_playbooks)
        if not_registered_tests:
            not_registered_tests_string = '\n'.join(not_registered_tests)
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
        with open(self.CONF_PATH, 'w') as file:
            json.dump(conf_json_content, file, indent=4)

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
