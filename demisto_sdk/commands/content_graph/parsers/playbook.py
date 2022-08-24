import networkx
from pathlib import Path
from typing import Any, Dict

from demisto_sdk.commands.common.update_id_set import (
    BUILT_IN_FIELDS,
    get_fields_by_script_argument,
    build_tasks_graph
)
from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import YAMLContentItemParser


LIST_COMMANDS = ['Builtin|||setList', 'Builtin|||getList']

class PlaybookParser(YAMLContentItemParser, content_type=ContentTypes.PLAYBOOK):
    def __init__(self, path: Path, is_test: bool = False) -> None:
        """ Builds a directed graph representing the playbook and parses it.

        Args:
            path (Path): The playbook path.
            is_test (bool, optional): Whether this is a test playbook or not. Defaults to False.
        """
        super().__init__(path)
        self.is_test: bool = is_test
        self.graph: networkx.DiGraph = build_tasks_graph(self.yml_data)
        self.connect_to_dependencies()
        self.connect_to_tests()

    @property
    def object_id(self) -> str:
        return self.yml_data.get('id')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.PLAYBOOK
    
    def is_mandatory_dependency(self, task_id: str) -> bool:
        try:
            return self.graph.nodes[task_id]['mandatory']
        except KeyError:
            # task is not connected to a branch
            return False

    def handle_playbook_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """ Collects a playbook dependency.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if playbook := task.get('task', {}).get('playbookName'):
            self.add_dependency(playbook, ContentTypes.PLAYBOOK, is_mandatory)

    def handle_script_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """ Collects a script dependency.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if script := task.get('task', {}).get('scriptName'):
            self.add_dependency(script, ContentTypes.SCRIPT, is_mandatory)

    def handle_command_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """ Collects dependencies in a commands task.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if command := task.get('task', {}).get('script'):
            if 'setIncident' in command:
                for incident_field in get_fields_by_script_argument(task):
                    self.add_dependency(incident_field, ContentTypes.INCIDENT_FIELD, is_mandatory)

            elif 'setIndicator' in command:
                for incident_field in get_fields_by_script_argument(task):
                    self.add_dependency(incident_field, ContentTypes.INDICATOR_FIELD, is_mandatory)

            elif command in LIST_COMMANDS:
                if list := task.get('scriptarguments', {}).get('listName', {}).get('simple'):
                    self.add_dependency(list, ContentTypes.LIST, is_mandatory)

            elif 'Builtin' not in command:
                if '|' not in command:
                    self.add_dependency(command, ContentTypes.COMMAND, is_mandatory)
                else:
                    integration, *_, command = command.split('|')
                    if integration:
                        self.add_dependency(integration, ContentTypes.INTEGRATION, is_mandatory)
                    else:
                        self.add_dependency(command, ContentTypes.COMMAND, is_mandatory)

    def add_complex_input_filters_and_transformers(self, complex_input: Dict[str, Any], is_mandatory: bool) -> None:
        for filter in complex_input.get('filters', []):
            if filter:
                operator = filter[0].get('operator')
                self.add_dependency(operator, ContentTypes.SCRIPT, is_mandatory)

        for transformer in complex_input.get('transformers', []):
            if transformer:
                operator = transformer.get('operator')
                self.add_dependency(operator, ContentTypes.SCRIPT, is_mandatory)

    def handle_task_filter_and_transformer_scripts(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """ Collects filters/transformers in a task as dependencies.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if task.get('type') == 'condition':
            for condition_entry in task.get('conditions', []):
                for inner_condition in condition_entry.get('condition', []):
                    for condition in inner_condition:
                        if condition_lhs := condition.get('left', {}).get('value', {}).get('complex', {}):
                            self.add_complex_input_filters_and_transformers(condition_lhs, is_mandatory)
                        if condition_rhs := condition.get('right', {}).get('value', {}).get('complex', {}):
                            self.add_complex_input_filters_and_transformers(condition_rhs, is_mandatory)
        else:
            for script_argument in task.get('scriptarguments', {}).values():
                if arg_value := script_argument.get('complex', {}):
                    self.add_complex_input_filters_and_transformers(arg_value, is_mandatory)

    def handle_field_mapping(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        if field_mapping := task.get('task', {}).get('fieldMapping'):
            for incident_field in field_mapping:
                if incident_field not in BUILT_IN_FIELDS:
                    self.add_dependency(incident_field, ContentTypes.INCIDENT_FIELD, is_mandatory)

    def connect_to_dependencies(self) -> None:
        """ Collects content items used by the playbook as dependencies.
        Whether or not they are mandatory is determined by their "mandatory" task node fields
        in the graph representation.
        """
        for task_id, task in self.yml_data.get('tasks', {}).items():
            is_mandatory = self.is_mandatory_dependency(task_id)
            self.handle_task_filter_and_transformer_scripts(task, is_mandatory)
            self.handle_playbook_task(task, is_mandatory)
            self.handle_script_task(task, is_mandatory)
            self.handle_command_task(task, is_mandatory)
            self.handle_field_mapping(task, is_mandatory)
