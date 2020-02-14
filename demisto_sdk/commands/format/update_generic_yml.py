import os
import sys
import yaml
import yamlordereddictloader

from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


class BaseUpdateYML:
    """BaseUpdateYML is the base class for all updaters.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """

    DEFAULT_YML_VERSION = -1
    ID_AND_VERSION_PATH_BY_YML_TYPE = {
        'IntegrationYMLFormat': 'commonfields',
        'ScriptYMLFormat': 'commonfields',
        'PlaybookYMLFormat': '',
    }

    def __init__(self, source_file='', output_file_name=''):
        self.source_file = source_file

        if not self.source_file:
            print_color('Please provide <source path>, <optional - destination path>.', LOG_COLORS.RED)
            sys.exit(1)

        try:
            self.yml_data = self.get_yml_data_as_dict()
        except yaml.YAMLError:
            print_color('Provided file is not a valid YML.', LOG_COLORS.RED)
            sys.exit(1)

        self.output_file_name = self.set_output_file_name(output_file_name)
        self.id_and_version_location = self.get_id_and_version_path_object()

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

    def get_yml_data_as_dict(self):
        """Converts YML file data to Dict.

        Returns:
            Dict. Data from YML.
        """
        print(F'Reading YML data')

        with open(self.source_file) as f:
            return yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    def get_id_and_version_path_object(self):
        """Gets the dict that holds the id and version fields.

        Returns:
            Dict. Holds the id and version fields.
        """
        yml_type = self.__class__.__name__
        path = self.ID_AND_VERSION_PATH_BY_YML_TYPE[yml_type]
        return self.yml_data.get(path, self.yml_data)

    def remove_copy_and_dev_suffixes_from_name(self):
        """Removes any _dev and _copy suffixes in the file.

        When developer clones playbook/integration/script it will automatically add _copy or _dev suffix.
        """
        print(F'Removing _dev and _copy suffixes from name and display tags')

        self.yml_data['name'] = self.yml_data.get('name', '').replace('_copy', '').replace('_dev', '')
        if self.yml_data.get('display'):
            self.yml_data['display'] = self.yml_data.get('display', '').replace('_copy', '').replace('_dev', '')

    def update_id_to_equal_name(self):
        """Updates the id of the YML to be the same as it's name."""
        print(F'Updating YML ID to be the same as YML name')

        self.id_and_version_location['id'] = self.yml_data['name']

    def set_version_to_default(self):
        """Replaces the version of the YML to default."""
        print(F'Setting YML version to default: {self.DEFAULT_YML_VERSION}')

        self.id_and_version_location['version'] = self.DEFAULT_YML_VERSION

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        print(F'Saving output YML file to {self.output_file_name}')

        # Configure safe dumper (multiline for strings)
        yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str

        def repr_str(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
            return dumper.org_represent_str(data)
        yaml.add_representer(str, repr_str, Dumper=yamlordereddictloader.SafeDumper)

        with open(self.output_file_name, 'w') as f:
            yaml.dump(
                self.yml_data,
                f,
                Dumper=yamlordereddictloader.SafeDumper,
                default_flow_style=False)

    def update_yml(self):
        """Manager function for the generic YML updates."""
        print_color(F'=======Starting updates for YML: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.remove_copy_and_dev_suffixes_from_name()
        self.update_id_to_equal_name()
        self.set_version_to_default()

        print_color(F'=======Finished generic updates for YML: {self.output_file_name}=======', LOG_COLORS.YELLOW)

    def initiate_file_validator(self, validator_type, scheme_type):
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
