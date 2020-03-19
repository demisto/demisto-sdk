import os
import json
import yaml
from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


class BaseUpdateJSON:
    """BaseUpdateJSON is the base class for all json updaters.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            json_data (Dict): YML file data arranged in a Dict.
    """

    DEFAULT_JSON_VERSION = -1
    NEW_FILE_DEFAULT_FROMVERSION = '5.0.0'
    OLD_FILE_DEFAULT_FROMVERSION = '1.0.0'

    def __init__(self, input='', output='', old_file='', path='', from_version=''):
        self.fromVersion = True
        self.source_file = input
        self.old_file = old_file
        self.path = path
        self.from_version = from_version
        if not self.source_file:
            raise Exception('Please provide <source path>, <optional - destination path>.')

        try:
            self.json_data = self.get_json_data_as_dict()
        except json.JSONDecodeError:
            raise Exception('Provided file is not a valid YML.')
        self.output_file_name = self.set_output_file_name(output)
        self.arguments_to_remove = self.arguments_to_remove()

    def set_output_file_name(self, output_file_name):
        """Creates and format the output file name according to user input.

        Args:
            output_file_name: The output file name the user defined.

        Returns:
            str. the full formatted output file name.
        """
        source_dir = os.path.dirname(self.source_file)
        file_name = os.path.basename(output_file_name or self.source_file)

        if self.__class__.__name__ == 'PlaybookYMLFormat':
            if not file_name.startswith('playbook-'):
                file_name = F'playbook-{file_name}'

        return os.path.join(source_dir, file_name)

    def get_json_data_as_dict(self):
        """Converts JSON file data to Dict.

        Returns:
            Dict. Data from JSON.
        """
        print(F'Reading JSON data')

        with open(self.source_file) as file:
            return json.load(file)

    def set_version_to_default(self):
        """Replaces the version of the YML to default."""
        print(F'Setting JSON version to default: {self.DEFAULT_JSON_VERSION}')

        self.json_data['version'] = self.DEFAULT_JSON_VERSION

    def set_fromVersion(self, from_version=None):
        """Set fromVersion to default if not exist."""
        "only for added files"
        # for new added files, set prefered fromVersion field, givven or default
        if not self.old_file:
            print(F'Setting fromVersion field in json file')
            # in all json files in repo the fromVersion is set to "fromVersion"
            if "fromVersion" not in self.json_data:
                if from_version:
                    self.json_data['fromVersion'] = from_version
                else:
                    self.json_data['fromVersion'] = self.NEW_FILE_DEFAULT_FROMVERSION
        # for modified files, set prefered fromVersion field, givven or default
        else:
            # in all json files in repo the fromVersion is set to "fromVersion"
            if "fromVersion" not in self.json_data:
                if from_version:
                    self.json_data['fromVersion'] = from_version
                else:
                    self.json_data['fromVersion'] = self.OLD_FILE_DEFAULT_FROMVERSION

    def set_default_values_as_needed(self, ARGUMENTS_DEFAULT_VALUES):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        print(F'Updating required default values')

        for field in ARGUMENTS_DEFAULT_VALUES:
            self.json_data[field] = ARGUMENTS_DEFAULT_VALUES[field]

    def remove_unnecessary_keys(self):
        print(F'Removing Unnecessary fields from file')
        for key in self.arguments_to_remove:
            print(F'Removing Unnecessary fields from file, key {key}')
            self.json_data.pop(key, None)

    def save_json_to_destination_file(self):
        """Save formatted JSON data to destination file."""
        print(F'Saving output JSON file to {self.output_file_name}')
        with open(self.output_file_name, 'w') as file:
            json.dump(self.json_data, file, indent=4)

    def update_json(self):
        """Manager function for the generic JSON updates."""
        print_color(F'=======Starting updates for JSON: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.set_version_to_default()
        self.remove_unnecessary_keys()
        self.set_fromVersion(from_version=self.from_version)

        print_color(F'=======Finished generic updates for JSON: {self.output_file_name}=======', LOG_COLORS.YELLOW)

    def initiate_file_validator(self, validator_type):
        print_color('Starting validating files structure', LOG_COLORS.GREEN)

        old_file_path = None
        if isinstance(self.source_file, tuple):
            old_file_path, file_path = self.source_file
        structure_validator = StructureValidator(self.source_file, old_file_path=old_file_path)

        validator = validator_type(structure_validator)

        if structure_validator.is_valid_file() and validator.is_valid_file(validate_rn=False):
            print_color('The files are valid', LOG_COLORS.GREEN)
            return 0

        else:
            print_color('The files are invalid', LOG_COLORS.RED)
            return 1

    def format_file(self):
        pass

    def arguments_to_remove(self):
        arguments_to_remove = []
        with open(self.path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        schema_fields = a.get('mapping').keys()
        file_fields = self.json_data.keys()
        for field in file_fields:
            if field not in schema_fields:
                arguments_to_remove.append(field)
        return arguments_to_remove
