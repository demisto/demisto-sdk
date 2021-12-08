import json
import os
from collections import OrderedDict
from typing import Optional

from genericpath import exists

from demisto_sdk.commands.common.constants import (DEFAULT_ID_SET_PATH,
                                                   GENERIC_COMMANDS_NAMES,
                                                   MarketplaceVersions,
                                                   MP_V2_ID_SET_PATH)
from demisto_sdk.commands.common.update_id_set import re_create_id_set


class IDSetCreator:

    def __init__(self, output: Optional[str] = '', input: Optional[str] = None, print_logs: bool = True,
                 fail_duplicates: bool = False, marketplace: str = 'xsoar'):
        """IDSetCreator

        Args:
            input (str, optional): The input path. the default input is the content repo.
            output (str, optional): The output path. Set to None to avoid creation of a file. '' means the default path.
             Defaults to 'Tests/id_set.json'.
            print_logs (bool, optional): Print log output. Defaults to True.
            fail_duplicates(bool, optional): Flag which marks whether create_id_set fails when duplicates
             are found or not
        """
        self.output = output
        self.input = input
        self.print_logs = print_logs
        self.fail_duplicates = fail_duplicates
        self.id_set = OrderedDict()  # type: ignore
        self.marketplace = marketplace.lower()

    def create_id_set(self):
        self.id_set = re_create_id_set(
            id_set_path=self.output,
            pack_to_create=self.input,
            print_logs=self.print_logs,
            fail_on_duplicates=self.fail_duplicates,
            marketplace=self.marketplace
        )
        self.add_command_to_implementing_integrations_mapping()
        self.save_id_set()
        return self.id_set

    def add_command_to_implementing_integrations_mapping(self):
        """
        Modifies playbook set in id_set dictionary once it was created.
        Each playbook that has "command_to_integration" field will be modified :
        - command name value will be a list of all integrations that implements this command (instead of use "" ).
        """
        command_name_to_implemented_integration_map = self.create_command_to_implemented_integration_map()

        playbooks_list = self.id_set['playbooks']
        for playbook_dict in playbooks_list:
            playbook_name = list(playbook_dict.keys())[0]
            playbook_data = playbook_dict[playbook_name]
            commands_to_integration = playbook_data.get("command_to_integration", {})
            for command in commands_to_integration:
                if commands_to_integration[command]:
                    # only apply this logic when there is no specific brand
                    continue
                is_command_implemented_in_integration = command in command_name_to_implemented_integration_map
                if is_command_implemented_in_integration and command not in GENERIC_COMMANDS_NAMES:
                    implemented_integration = command_name_to_implemented_integration_map[command]
                    commands_to_integration[command] = implemented_integration

    def create_command_to_implemented_integration_map(self):
        command_name_to_implemented_integration_map = {}  # type: ignore
        integrations_list = self.id_set['integrations']
        for integration_data in integrations_list:
            integration_name = list(integration_data.keys())[0]
            integration_data = integration_data[integration_name]
            commands = integration_data.get("commands", {})
            for command in commands:
                if command in command_name_to_implemented_integration_map:
                    command_name_to_implemented_integration_map[command] += [integration_name]
                else:
                    command_name_to_implemented_integration_map[command] = [integration_name]
        return command_name_to_implemented_integration_map

    def save_id_set(self):
        if not self.output:
            self.output = MP_V2_ID_SET_PATH if self.marketplace == MarketplaceVersions.MarketplaceV2.value \
                else DEFAULT_ID_SET_PATH
        if not exists(self.output):
            intermediate_dirs = os.path.dirname(os.path.abspath(self.output))
            os.makedirs(intermediate_dirs, exist_ok=True)
        with open(self.output, 'w+') as id_set_file:
            json.dump(self.id_set, id_set_file, indent=4)
