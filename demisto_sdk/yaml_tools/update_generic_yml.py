import sys
import ntpath
import yaml
import yamlordereddictloader
from demisto_sdk.common.tools import print_color, LOG_COLORS


class UpdateGenericYML:

    def __init__(self, source_path='', destination_path=''):
        self.source_path = source_path
        self.destination_path = destination_path

        if not self.source_path:
            print_color('Please provide <source path>, <optional - destination path>', LOG_COLORS.RED)
            sys.exit(1)

        self.yml_data = self.get_yml_data_as_dict()

    def get_yml_data_as_dict(self):
        """Converts YML file data to Dict.

        Returns:
            Dict. Data from YML.

        """
        with open(self.source_path) as f:
            return yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    def update_replace_copy_dev(self):
        """Removes any _dev and _copy suffixes in the file.

        When developer clones playbook/integration/script it will automatically add _copy or _dev suffix.
        """
        self.yml_data['name'] = self.yml_data.get('name', '').replace('_copy', '').replace('_dev', '')
        self.yml_data['id'] = self.yml_data.get('id', '').replace('_copy', '').replace('_dev', '')

        for task_id, playbook_task in self.yml_data.get('tasks', {}).items():
            inner_task = playbook_task.get('task', {})

            possible_labels_to_modify = ['scriptName', 'playbookName', 'script']

            for label in possible_labels_to_modify:
                if label in inner_task:
                    inner_task[F'{label}'] = inner_task[F'{label}'].replace('_copy', '').replace('_dev', '')

    def update_yml(self):
        print_color(F'========Starting update for playbook {self.source_path}========', LOG_COLORS.YELLOW)
