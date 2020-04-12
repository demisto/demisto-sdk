import yaml
import yamlordereddictloader
from demisto_sdk.commands.common.tools import LOG_COLORS, print_color
from demisto_sdk.commands.format.update_generic import BaseUpdate
from ruamel.yaml import YAML

ryaml = YAML()
ryaml.allow_duplicate_keys = True


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

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate)
        self.id_and_version_location = self.get_id_and_version_path_object()

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
        print(F'Updating YML ID to be the same as YML name')
        self.id_and_version_location['id'] = self.data['name']

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        print(F'Saving output YML file to {self.output_file}')
        # Configure safe dumper (multiline for strings)
        yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str

        def repr_str(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
            return dumper.org_represent_str(data)

        yaml.add_representer(str, repr_str, Dumper=yamlordereddictloader.SafeDumper)

        with open(self.output_file, 'w') as f:
            ryaml.dump(
                self.data,
                f)

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
