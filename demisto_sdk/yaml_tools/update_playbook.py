from argparse import ArgumentDefaultsHelpFormatter

from demisto_sdk.common.tools import print_color, LOG_COLORS
from demisto_sdk.yaml_tools.update_generic_yml import BaseUpdateYML


class PlaybookYMLFormat(BaseUpdateYML):
    """PlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def add_description(self):
        """Add empty description to playbook and tasks of type title, start, end."""
        print_color(F'Adding empty descriptions to relevant tasks', LOG_COLORS.NATIVE)

        possible_labels_to_modify = ['start', 'end', 'title', 'playbook']

        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task.get('type', '') in possible_labels_to_modify:
                task['task'].update({'description': ''})

    def update_playbook_task_name(self):
        """Updates the name of the task to be the same as playbookName it is running."""
        print_color(F'Updating name of tasks who calls other playbooks to their name', LOG_COLORS.NATIVE)

        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task.get('type', '') == 'playbook':
                task['task']['name'] = task['task']['playbookName']

    def format_file(self):
        """Manager function for the playbook YML updater."""
        super().update_yml()

        print_color(F'========Starting updates for playbook: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.add_description()
        self.update_playbook_task_name()
        self.save_yml_to_destination_file()

        print_color(F'========Finished updates for playbook: {self.output_file_name}=======', LOG_COLORS.YELLOW)

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run formatter on a given playbook yml file. """
        parser = subparsers.add_parser('format', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-t", "--type", help="The type of yml file to be formatted.", required=True)
        parser.add_argument("-p", "--path", help="The path of the playbook yml file", required=True)
        parser.add_argument("-o", "--output-file", help="The path where the formatted file will be saved to")
