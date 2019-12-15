from argparse import ArgumentDefaultsHelpFormatter

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
        """Add empty description to playbook and tasks of type title, start, end.
        """
        possible_labels_to_modify = ['start', 'end', 'title', 'playbook']

        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task.get('type', '') in possible_labels_to_modify:
                task['task']['description'] = ''

    def update_playbook_task_name(self):
        """Updates the name of the task to be the same as playbookName it is running.
        """
        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task.get('type', '') == 'playbook':
                task['task']["name"] = task['task']['playbookName']

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run formatter on a given playbook yml file. """
        parser = subparsers.add_parser('format', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-p", "--path", help="Specify path of playbook yml file", required=True)
        parser.add_argument("-o", "--output-file", help="Specify path where the formatted file will be saved to")
