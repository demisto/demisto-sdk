import sys
import ntpath
import yaml
import yamlordereddictloader
from demisto_sdk.common.tools import print_color, LOG_COLORS


class UpdateGenericYML:
    DEFAULT_YML_VERSION = -1
    ID_AND_VERSION_PATH_BY_YML_TYPE = {
        'class IntegrationYMLFormat': 'commonfields',
        'class ScriptYMLFormat': 'commonfields',
        'class PlaybookYMLFormat': '',
    }

    def __init__(self, source_path='', destination_path=''):
        self.source_path = source_path
        self.destination_path = destination_path

        if not self.source_path:
            print_color('Please provide <source path>, <optional - destination path>', LOG_COLORS.RED)
            sys.exit(1)

        self.id_and_version_location = self.get_id_and_version_path_object()
        self.yml_data = self.get_yml_data_as_dict()

    def get_yml_data_as_dict(self):
        """Converts YML file data to Dict.

        Returns:
            Dict. Data from YML.
        """
        with open(self.source_path) as f:
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
        """Updates the id of the yml to be the same as it's name.
        """
        self.id_and_version_location['id'] = self.yml_data['name']

    def set_version_to_default(self):
        """Replaces the version of yml to -1
        """
        self.id_and_version_location['version'] = self.DEFAULT_YML_VERSION

    def update_yml(self):
        print_color(F'========Starting update for playbook {self.source_path}========', LOG_COLORS.YELLOW)

        self.remove_copy_and_dev_suffixes_from_name()
        self.update_id_to_equal_name()
        self.set_version_to_default()

