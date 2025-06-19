from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.common.update_id_set import (
    BUILT_IN_FIELDS,
    build_tasks_graph,
    get_fields_by_script_argument,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.playbook import StrictPlaybook

LIST_COMMANDS = ["Builtin|||setList", "Builtin|||getList"]
IGNORED_FIELDS = [
    "appendTags",
    "addLabels",
    "appendMultiSelect",
    "deleteEmptyField",
    "execution-timeout",
    "extend-context",
    "ignore-outputs",
    "retry-count",
    "retry-interval",
    "using",
]


class BasePlaybookParser(YAMLContentItemParser, content_type=ContentType.BASE_PLAYBOOK):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        is_test_playbook: bool = False,
        git_sha: Optional[str] = None,
    ) -> None:
        """Builds a directed graph representing the playbook and parses it.

        Args:
            path (Path): The playbook path.
            is_test_playbook (bool, optional): Whether this is a test playbook or not. Defaults to False.
        """
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.tags: List[str] = self.yml_data.get("tags", [])
        self.is_test: bool = is_test_playbook
        self.graph: networkx.DiGraph = build_tasks_graph(self.yml_data)
        self.connect_to_dependencies()
        self.connect_to_tests()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"object_id": "id", "tasks": "tasks", "quiet": "quiet"}
        )
        return super().field_mapping

    def is_mandatory_dependency(self, task_id: str) -> bool:
        try:
            return self.graph.nodes[task_id]["mandatory"]
        except KeyError:
            # task is not connected to a branch
            return False

    def handle_playbook_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """Collects a playbook dependency.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if playbook := (
            task.get("task", {}).get("playbookName")
            or task.get("task", {}).get("playbookId")
        ):
            self.add_relationship(
                RelationshipType.USES_PLAYBOOK,
                target=playbook,
                target_type=ContentType.PLAYBOOK,
                mandatorily=is_mandatory,
            )

    @property
    def quiet(self) -> bool:
        return get_value(self.yml_data, self.field_mapping.get("quiet", ""), False)

    @property
    def tasks(self) -> Optional[Dict]:
        return get_value(self.yml_data, self.field_mapping.get("tasks", ""), {})

    def handle_script_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """Collects a script dependency.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if script := task.get("task", {}).get("scriptName"):
            self.add_dependency_by_id(script, ContentType.SCRIPT, is_mandatory)

    def handle_command_task(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        """Collects dependencies in a commands task.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if command := task.get("task", {}).get("script"):
            if "setIncident" in command:
                for indicator_field in get_fields_by_script_argument(task):
                    if indicator_field and indicator_field not in IGNORED_FIELDS:
                        self.add_dependency_by_cli_name(
                            indicator_field,
                            ContentType.INCIDENT_FIELD,
                            is_mandatory=False,
                        )

            elif "setIndicator" in command:
                for indicator_field in get_fields_by_script_argument(task):
                    if indicator_field and indicator_field not in IGNORED_FIELDS:
                        self.add_dependency_by_cli_name(
                            indicator_field,
                            ContentType.INDICATOR_FIELD,
                            is_mandatory=False,
                        )

            elif command in LIST_COMMANDS:
                # if list := task.get('scriptarguments', {}).get('listName', {}).get('simple'):
                #     self.add_dependency_by_id(list, ContentType.LIST, is_mandatory)
                pass  # TODO: CIAC-4017

            elif "Builtin" not in command:
                if "|" not in command:
                    self.add_command_or_script_dependency(command, is_mandatory)
                else:
                    integration, *_, command = command.split("|")
                    if integration:
                        self.add_dependency_by_id(
                            integration, ContentType.INTEGRATION, is_mandatory
                        )
                    else:
                        self.add_dependency_by_id(
                            command, ContentType.COMMAND, is_mandatory
                        )

    def add_complex_input_filters_and_transformers(
        self, complex_input: Dict[str, Any], is_mandatory: bool
    ) -> None:
        for filter in complex_input.get("filters", []):
            if filter:
                operator = filter[0].get("operator").split(".")[-1]
                self.add_dependency_by_id(operator, ContentType.SCRIPT, is_mandatory)

        for transformer in complex_input.get("transformers", []):
            if transformer:
                operator = transformer.get("operator").split(".")[-1]
                self.add_dependency_by_id(operator, ContentType.SCRIPT, is_mandatory)

    def handle_task_filter_and_transformer_scripts(
        self, task: Dict[str, Any], is_mandatory: bool
    ) -> None:
        """Collects filters/transformers in a task as dependencies.

        Args:
            task (Dict[str, Any]): The task details.
            is_mandatory (bool): Whether or not the dependency is mandatory.
        """
        if task.get("type") == "condition":
            for condition_entry in task.get("conditions", []):
                for inner_condition in condition_entry.get("condition", []):
                    for condition in inner_condition:
                        if (
                            condition_lhs := condition.get("left", {})
                            .get("value", {})
                            .get("complex", {})
                        ):
                            self.add_complex_input_filters_and_transformers(
                                condition_lhs, is_mandatory
                            )
                        if (
                            condition_rhs := condition.get("right", {})
                            .get("value", {})
                            .get("complex", {})
                        ):
                            self.add_complex_input_filters_and_transformers(
                                condition_rhs, is_mandatory
                            )
        else:
            for script_argument in task.get("scriptarguments", {}).values():
                if arg_value := script_argument.get("complex", {}):
                    self.add_complex_input_filters_and_transformers(
                        arg_value, is_mandatory
                    )

    def handle_field_mapping(self, task: Dict[str, Any], is_mandatory: bool) -> None:
        if field_mapping := task.get("task", {}).get("fieldMapping"):
            for incident_field in field_mapping:
                if incident_field not in BUILT_IN_FIELDS:
                    self.add_dependency_by_cli_name(
                        incident_field, ContentType.INCIDENT_FIELD, is_mandatory
                    )

    def connect_to_dependencies(self) -> None:
        """Collects content items used by the playbook as dependencies.
        Whether or not they are mandatory is determined by their "mandatory" task node fields
        in the graph representation.
        """
        for task_id, task in self.yml_data.get("tasks", {}).items():
            is_mandatory = self.is_mandatory_dependency(task_id)
            self.handle_task_filter_and_transformer_scripts(task, is_mandatory)
            self.handle_playbook_task(task, is_mandatory)
            self.handle_script_task(task, is_mandatory)
            self.handle_command_task(task, is_mandatory)
            self.handle_field_mapping(task, is_mandatory)

    @property
    def strict_object(self):
        return StrictPlaybook  # both for Playbooks and TPBs
