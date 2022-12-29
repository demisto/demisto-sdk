from typing import Dict, List, Optional


class DeprecationValidator:
    """
    DeprecationValidator is designed to validate that there's no use for deprecated content items inside other
    non-deprecated content items.
    """

    def __init__(self, id_set_file: Dict[str, List]):
        self.script_section = id_set_file.get("scripts", [])
        self.playbook_section = id_set_file.get("playbooks", [])

    def validate_integartion_commands_deprecation(
        self, deprecated_commands_list: List[str], integration_id: str
    ):
        """
        Manages the deprecation usage for integration commands
        Checks if the given deprecated integration commands are used in a none-deprecated scripts / playbooks

        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            integration_id (str): The id of the integration that is currently being tested.

        Return:
            dict: A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks.
            The values are the file names where they're being used
        """
        usage_dict: Dict[str, list] = {}

        usage_dict = (
            self.collect_non_deprecated_playbooks_implementing_the_acommand_list(
                deprecated_commands_list, usage_dict, integration_id
            )
        )
        usage_dict = (
            self.collect_non_deprecated_scripts_implemeting_integration_commands(
                deprecated_commands_list, usage_dict
            )
        )

        return usage_dict

    def validate_playbook_deprecation(self, playbook_name: str):
        """
        Manages the deprecation usage validation for playbooks.
        Checks if the given deprecated playbook is used in a none-deprecated playbooks.

        Args:
            playbook_name (str): The name of the playbook.

        Return:
            list: A list of all the none-deprecated files that are using the given playbook.
        """
        usage_list: List[str] = []
        key_to_check = "implementing_playbooks"

        usage_list = (
            self.collect_non_deprecated_playbooks_that_use_a_given_playbook_or_script(
                playbook_name, usage_list, key_to_check
            )
        )

        return usage_list

    def validate_script_deprecation(self, script_name: str):
        """
        Manages the deprecation usage validation for scripts.
        Checks if the given deprecated script is used in a none-deprecated playbooks / scripts.

        Args:
            script_name (str): The name of the script.

        Return:
            list: A list of all the none-deprecated files that are using the given script.
        """
        usage_list: List[str] = []
        key_to_check = "implementing_scripts"

        usage_list = self.collect_non_deprecated_scripts_implemeting_another_script(
            script_name, usage_list
        )
        usage_list = (
            self.collect_non_deprecated_playbooks_that_use_a_given_playbook_or_script(
                script_name, usage_list, key_to_check
            )
        )

        return usage_list

    def collect_non_deprecated_playbooks_implementing_the_acommand_list(
        self, deprecated_commands_list, usage_dict: Dict[str, list], integration_id: str
    ):
        """
        Filter the relevant playbooks for the current integration validation from the playbook_section
        and check which of the integration commands are being used in this files using the validate_integration_not_in_playbook function.

        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands
            that are used in none-deprecated scripts / playbooks.
            The values are the file names where they're being used.
            integration_id (str): The id of the integration that is currently being tested.
        """
        for playbook in self.playbook_section:
            for playbook_val in playbook.values():
                if playbook_val.get("deprecated"):
                    continue
                command_to_integration = playbook_val.get("command_to_integration")
                if command_to_integration:
                    usage_dict = self.validate_integration_commands_not_in_playbook(
                        usage_dict,
                        deprecated_commands_list,
                        command_to_integration,
                        playbook_val,
                        integration_id,
                    )
        return usage_dict

    def validate_integration_commands_not_in_playbook(
        self,
        usage_dict: Dict,
        deprecated_commands_list: List[str],
        command_to_integration: Dict[str, list],
        playbook: Dict,
        integration_id: str,
    ):
        """
        List all the integration commands of the current checked integration that are being used in the given playbook.
        and update them in the given usage_dict.

        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands
            that are used in none-deprecated scripts / playbooks.
            The values are the file names where they're being used.
            command_to_integration(dict) A dict where the keys are the integartions commands that are being used
            and the value is the integration name.
            playbook (dict): The playbook currently being checked.
            integration_id (str): The id of the integration that is currently being tested.
        """
        for command, integration_name in command_to_integration.items():
            if command in deprecated_commands_list:
                if integration_name == integration_id or not integration_name:
                    playbook_path: Optional[str] = playbook.get("file_path", "")
                    if command in usage_dict and playbook_path not in usage_dict.get(
                        command, []
                    ):
                        usage_dict.get(command, []).append(playbook_path)
                    if command not in usage_dict:
                        usage_dict[command] = [playbook_path]
        return usage_dict

    def collect_non_deprecated_scripts_implemeting_integration_commands(
        self, deprecated_commands_list: List[str], usage_dict: Dict
    ):
        """
        List all the integration commands of the current checked integration that are being used in the none-deprecated scripts
        and update them in the given usage_dict.

        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands
            that are used in none-deprecated scripts / playbooks.
            The values are the file names where they're being used.
        """
        for script in self.script_section:
            for script_val in script.values():
                if script_val.get("deprecated"):
                    continue
                depends_commads_list = script_val.get("depends_on")
                if depends_commads_list:
                    for command in depends_commads_list:
                        if command in deprecated_commands_list:
                            script_path = script_val.get("file_path", "")
                            if (
                                command in usage_dict
                                and script_path not in usage_dict.get(command, [])
                            ):
                                usage_dict.get(command, []).append(script_path)
                            elif command not in usage_dict:
                                usage_dict[command] = [script_path]
        return usage_dict

    def collect_non_deprecated_scripts_implemeting_another_script(
        self, script_name: str, usage_list: List[str]
    ):
        """
        List all the paths of scripts that are using the given script and are non-deprecated.

        Args:
            script_name (str): The name of the script that is currently being checked.
            usage_list (list): A list of all the files that use the given script to update the found scripts into.
        """
        for script in self.script_section:
            for script_val in script.values():
                if script_val.get("deprecated"):
                    continue
                depends_commads_list = script_val.get("depends_on")
                if depends_commads_list and script_name in depends_commads_list:
                    usage_list.append(script_val.get("file_path"))
        return usage_list

    def collect_non_deprecated_playbooks_that_use_a_given_playbook_or_script(
        self, curent_entity_name: str, usage_list: List[str], key_to_check: str
    ):
        """
        Collect from id_set all the playbooks that are non-deprecated and are implementing the given entity (script/playbook).

        Args:
            curent_entity_name (str): The name of the script / playbook currently being checked.
            usage_list (list): A list of all the file paths that are using the script / playbook currently being checked.
            key_to_check (str): The field in which the right entity to check is located at.
        """
        for playbook in self.playbook_section:
            for playbook_val in playbook.values():
                if playbook_val.get("deprecated"):
                    continue
                implementing_entities = playbook_val.get(key_to_check)
                if implementing_entities:
                    usage_list = self.find_implementing_playbooks_and_scripts(
                        usage_list,
                        curent_entity_name,
                        implementing_entities,
                        playbook_val,
                    )
        return usage_list

    def find_implementing_playbooks_and_scripts(
        self,
        usage_list: List[str],
        curent_entity_name: str,
        implementing_entities: List[str],
        playbook: Dict,
    ):
        """
        List all the playbooks paths of playbooks that are using the current checked playbook / script.

        Args:
            usage_list (list): A list of all the file paths that are using the script / playbook currently being checked.
            curent_entity_name (str): The name of the script / playbook currently being checked.
            implementing_entities(dict) A list of all the entites that this currently checked playbook is using.
            playbook (dict): The playbook currently being checked.
        """
        for implementing_entity in implementing_entities:
            if implementing_entity == curent_entity_name:
                usage_list.append(playbook.get("file_path", ""))
        return usage_list
