import os
import sys
import yaml
import yamlordereddictloader

from demisto_sdk.common.tools import print_color, LOG_COLORS


class BaseUpdateYML:
    """Base Update YML is the base class for all updaters.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
    """

    DEFAULT_YML_VERSION = -1
    ID_AND_VERSION_PATH_BY_YML_TYPE = {
        'class IntegrationYMLFormat': 'commonfields',
        'class ScriptYMLFormat': 'commonfields',
        'class PlaybookYMLFormat': '',
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

        :param output_file_name: The name the user defined.
        :return:
            str. the full formatted output file name.
        """
        file_name_builder = os.path.basename(output_file_name) or os.path.basename(self.source_file)

        if not file_name_builder.startswith('playbook-'):
            file_name_builder = F'playbook-{file_name_builder}'

        return file_name_builder

    def get_yml_data_as_dict(self):
        """Converts YML file data to Dict.

        Returns:
            Dict. Data from YML.
        """
        with open(self.source_file) as f:
            return yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    def get_id_and_version_path_object(self):
        """Gets the dict that holds the id and version fields.

        :return:
            Dict. Holds the id and version fields.
        """
        instance_name = str(type(self))
        path = self.ID_AND_VERSION_PATH_BY_YML_TYPE[instance_name]
        return self.yml_data.get(path, self)

    def remove_copy_and_dev_suffixes_from_name(self):
        """Removes any _dev and _copy suffixes in the file.

        When developer clones playbook/integration/script it will automatically add _copy or _dev suffix.
        """
        self.yml_data['name'] = self.yml_data.get('name', '').replace('_copy', '').replace('_dev', '')

    def update_id_to_equal_name(self):
        """Updates the id of the YML to be the same as it's name.
        """
        self.id_and_version_location['id'] = self.yml_data['name']

    def set_version_to_default(self):
        """Replaces the version of the YML to -1.
        """
        self.id_and_version_location['version'] = self.DEFAULT_YML_VERSION

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file.
        """
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
        """Manager function for the generic YML updates.
        """
        print_color(F'========Starting generic updates for YML: {self.source_file}========', LOG_COLORS.YELLOW)

        self.remove_copy_and_dev_suffixes_from_name()
        self.update_id_to_equal_name()
        self.set_version_to_default()

        print_color(F'========Finished generic updates for YML: {self.output_file_name}========', LOG_COLORS.YELLOW)
