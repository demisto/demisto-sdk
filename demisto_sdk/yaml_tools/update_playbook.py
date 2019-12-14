import sys
import ntpath
import yaml
import yamlordereddictloader

from demisto_sdk.yaml_tools.update_generic_yml import BaseUpdateYML


class PlaybookYMLFormat(BaseUpdateYML):

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
