import os
import sys
import json

from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


class BaseUpdateJSON:
    """BaseUpdateJSON is the base class for all updaters.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """

    DEFAULT_JSON_VERSION = -1
    DEFAULT_FROMVERSION = '5.0.0'

    def __init__(self, source_file='', output_file_name='', old_file=''):
        self.fromVersion = True
        self.source_file = source_file
        self.old_file = old_file
        if not self.source_file:
            print_color('Please provide <source path>, <optional - destination path>.', LOG_COLORS.RED)
            sys.exit(1)

        try:
            self.json_data = self.get_json_data_as_dict()
        except json.JSONDecodeError:
            print_color('Provided file is not a valid JSON.', LOG_COLORS.RED)
            sys.exit(1)

        self.output_file_name = self.set_output_file_name(output_file_name)

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

    def set_fromVersion(self):
        """Set fromVersion to default if not exist."""
        "only for added files"

        if not self.old_file:
            print(F'Setting fromversion field')
            if "fromVersion" not in self.json_data:
                self.json_data['fromVersion'] = self.DEFAULT_FROMVERSION

    def set_default_values_as_needed(self, ARGUMENTS_DEFAULT_VALUES):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        print(F'Updating required default values')

        for field in ARGUMENTS_DEFAULT_VALUES:
            self.json_data[field] = ARGUMENTS_DEFAULT_VALUES[field]

    def remove_unnecessary_keys(self, ARGUMENTS_TO_REMOVE):
        print(F'Removing Unnecessary fields from file')
        for key in ARGUMENTS_TO_REMOVE:
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
        self.set_fromVersion()

        print_color(F'=======Finished generic updates for JSON: {self.output_file_name}=======', LOG_COLORS.YELLOW)

    def initiate_file_validator(self, validator_type, scheme_type=None):
        print_color('Starting validating files structure', LOG_COLORS.GREEN)

        structure = StructureValidator(file_path=str(self.output_file_name), predefined_scheme=scheme_type)
        validator = validator_type(structure)

        if structure.is_valid_file() and validator.is_valid_file(validate_rn=False):
            print_color('The files are valid', LOG_COLORS.GREEN)
            return 0

        else:
            print_color('The files are invalid', LOG_COLORS.RED)
            return 1

    def format_file(self):
        pass
