

class DeprecationValidator:
    """
        DeprecationValidator is designed to validate that there's no use for deprecated content items inside other
        non-deprecated content items.
    """
    def __init__(self, id_set_file):
        self.script_section = [script for script in id_set_file.get("scripts") if ("depends_on" in script and not script.get("deprecated"))]
        self.playbook_section = id_set_file.get("playbooks")
        self.test_playbook_section = id_set_file.get("TestPlaybooks")

    def validate_integartion(self, deprecated_commands_list, test_playbooks_ls):
        """
        Manages the deprecation usage for integration commands
        Checks if the given deprecated integration commands are used in a none-deprecated scripts / playbooks / testplaybooks
        
        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            test_playbooks_ls (list): A list of all the tests that're related to the given integration. 

        Return:
            dict: A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks / testplaybooks.
            The values are the file names where they're being used
        """
        usage_dict = {}

        self.filter_testplaybooks_for_integration_validation(deprecated_commands_list, test_playbooks_ls, usage_dict)
        self.filter_playbooks_for_integration_validation(deprecated_commands_list, usage_dict)
        self.find_scripts_using_givin_integration_commands(deprecated_commands_list, usage_dict)
        
        return usage_dict

    def validate_playbook():
        pass

    def validate_script(self, script_name, test_playbooks_ls):
        usage_list = []
        self.find_scripts_using_givin_script(script_name, usage_list)

    def filter_testplaybooks_for_integration_validation(self, deprecated_commands_list, test_playbooks_ls, usage_dict):
        """
        Filter the relevant test_playbooks for the current integration validation from the test_playbook_section
        and check which of the integration commands are being used in this files using the validate_integration_not_in_playbook function.
        
        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            test_playbooks_ls (list): A list of all the tests that're related to the given integration.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks / testplaybooks.
            The values are the file names where they're being used.
        """
        for test_playbook in test_playbooks_ls:
            command_to_integration = self.test_playbook_section.get(test_playbook, {}).get("command_to_integration")
            if command_to_integration:
                self.validate_integration_commands_not_in_playbook(usage_dict, deprecated_commands_list, command_to_integration, test_playbook)

    def filter_playbooks_for_integration_validation(self, deprecated_commands_list, usage_dict):
        """
        Filter the relevant playbooks for the current integration validation from the playbook_section
        and check which of the integration commands are being used in this files using the validate_integration_not_in_playbook function.
        
        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks / testplaybooks.
            The values are the file names where they're being used.
        """
        for playbook in self.playbook_section:
            command_to_integration = playbook.get("command_to_integration")
            if command_to_integration:
                self.validate_integration_commands_not_in_playbook(usage_dict, deprecated_commands_list, command_to_integration, playbook)

    def validate_integration_commands_not_in_playbook(self, usage_dict, deprecated_commands_list, command_to_integration, playbook):
        """
        List all the integration commands of the current checked integration that are being used in the given playbook.
        and update them in the given usage_dict.

        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks / testplaybooks.
            The values are the file names where they're being used.
            command_to_integration(dict) A dict where the keys are the integartions commands that are being used
            and the value is the integration name.
            playbook (dict): The playbook currently being checked.
        """
        for command in command_to_integration.keys():
            if command in deprecated_commands_list:
                if command in usage_dict and (playbook_path := playbook.get("file_path")) not in usage_dict.get(command):
                    usage_dict[command] = usage_dict.get(command).append(playbook_path)
                if command not in usage_dict:
                    usage_dict[command] = [playbook.get("file_path")]

    def find_scripts_using_givin_integration_commands(self, deprecated_commands_list, usage_dict):
        """
        List all the integration commands of the current checked integration that are being used in the none-deprecated scripts
        and update them in the given usage_dict.
        
        Args:
            deprecated_commands_list (list): A list of all the integration's deprecated commands.
            usage_dict (dict): A dictionary where the keys are the integartion's deprecated commands that are used in none-deprecated  scripts / playbooks / testplaybooks.
            The values are the file names where they're being used.
        """
        for script in self.script_section:
            depends_commads_list = script.get("depends_on")
            for command in depends_commads_list:
                if command in deprecated_commands_list:
                    if command in usage_dict and (script_path := script.get("file_path")) not in usage_dict.get(command):
                        usage_dict[command] = usage_dict.get(command).append(script_path)
                    if command not in usage_dict:
                        usage_dict[command] = [script.get("file_path")]

    def find_scripts_using_givin_script(self, script_name, usage_list):
        """
        List all the scripts that are using the given script.
        
        Args:
            script_name (str): The name of the script that is currently being checked.
            usage_list (list): A list of all the files that use the given script to update the found scripts into.
        """
        for script in self.script_section:
            depends_commads_list = script.get("depends_on")
            if script_name in depends_commads_list:
                usage_list.append(script.get("file_path"))
