from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsCorrectValueReferencesInterface(BaseValidator[ContentTypes]):
    error_code = "PB121"
    description = (
        ""
    )
    rationale = ""
    error_message = (
        'In task: {task_name!r} with ID: {task_id!r}, an input with the value: {path!r} was passed as a string not a reference.'
        'Change the reference to "From previous tasks" from "As value", or change the value to ${{{path}}}.'
    )
    related_field = "conditions"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Check that references of context values, are valid, i.e. "iscontext: true" or surrounded by ${<condition>},
        Args:
            content_items (Iterable[ContentTypes]): The content items to check.
        Returns:
            List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for playbook in content_items:
            for task_id, task in playbook.tasks.items():
                
                is_task_valid = {
                    'condition': self.is_valid_condition_task,
                    'regular': self.is_valid_regular_task,
                    'collection': self.is_valid_data_collection,
                }.get(task.type, lambda *_: [])

                invalid_values = is_task_valid(task, task_id)

                results += [
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            task_id=task_id,
                            task_name=task.task.name,
                            path=value,
                        ),
                        content_object=playbook,
                    )
                    for value in invalid_values
                ]

        return results

    def is_valid_condition_task(self, task: TaskConfig) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a condition task
        Returns: True if the references are correct
        """
        invalid_values = []
        for conditions in task.conditions:
            for condition in conditions.get("condition"):
                for condition_info in condition:
                    invalid_values += (
                        self.get_invalid_values_of_side_in_condition_task('left', condition_info)
                        + self.get_invalid_values_of_side_in_condition_task('right', condition_info)
                    )
        for message_key, message_value in task.get("message", {}).items():
            invalid_values += self.get_invalid_message_values(message_key, message_value)
        for script_argument in task.get("scriptarguments", {}).values():
            invalid_values += self.handle_script_arguments(script_argument)
        return invalid_values

    def is_valid_regular_task(self, task: TaskConfig) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a regular task
        Returns: True if the references are correct
        """
        invalid_values = []
        if default_assignee := task.get("defaultassigneecomplex", {}).get("simple"):
            invalid_values += self.get_invalid_reference_values(default_assignee)
        elif default_assignee := task.get("defaultassigneecomplex", {}).get("complex", {}):
            invalid_values += self.handle_transformers_and_filters(default_assignee)
        for script_argument in task.get("scriptarguments", {}).values():
            invalid_values += self.handle_script_arguments(script_argument)
        for incident_field in task.get("fieldMapping", []):
            invalid_values += self.handle_transformers_and_filters(incident_field.get("output", {}).get("complex", {}))
        return invalid_values

    def is_valid_data_collection(self, task: TaskConfig):
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a data collection task
        Returns: True if the references are correct
        """
        invalid_values = []
        for script_argument in task.get("scriptarguments", {}).values():
            invalid_values += self.handle_script_arguments(script_argument)
        for message_key, message_value in task.get("message", {}).items():
            invalid_values += self.get_invalid_message_values(message_key, message_value)
        for form_question in task.get("form", {}).get("questions", []):
            if labelarg := form_question.get("labelarg", {}):
                if value := labelarg.get("simple", ""):
                    invalid_values += self.get_invalid_reference_values(value, labelarg)
                elif value := labelarg.get("complex", {}):
                    invalid_values += self.handle_transformers_and_filters(value)
        return invalid_values

    def handle_transformers_and_filters(self, field_output: dict) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a transformers and filters section.
        Returns: The invalid values
        """
        invalid_values = []
        for incident_filter in field_output.get("filters", []):
            for filter_info in incident_filter:
                invalid_values += (
                    self.get_invalid_values_of_side_in_condition_task('left', filter_info)
                    + self.get_invalid_values_of_side_in_condition_task('right', filter_info)
                )
        for transformer in field_output.get("transformers", []):
            for _, arg_info in transformer.get("args", {}).items():
                if value := arg_info.get("value", {}).get("simple", ""):
                    invalid_values += self.get_invalid_reference_values(value, arg_info)
        return invalid_values

    @staticmethod
    def get_invalid_reference_values(values: str, value_info: dict = {}) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        Returns: A list of invalid values
        """
        invalid_values = []
        split_values = values.split(",")
        for value in split_values:
            if value.startswith("incident.") or value.startswith("inputs."):
                if not value_info.get("iscontext", False):
                    invalid_values.append(value)
        return invalid_values

    def get_invalid_values_of_side_in_condition_task(self, side: str, condition_info: dict) -> list[str]:
        if (
            value := condition_info.get(side, {})
            .get("value", {})
            .get("simple", "")
        ):
            return self.get_invalid_reference_values(
                value,
                condition_info.get(side, {}),
            )
        elif (
            value := condition_info.get(side, {})
            .get("value", {})
            .get("complex", {})
        ):
            return self.handle_transformers_and_filters(value)

    def get_invalid_message_values(self, message_key, message_value) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a message section.
        Returns: A list of invalid values
        """
        if message_key and message_value and isinstance(message_value, dict):
            if value := message_value.get("simple"):
                return self.get_invalid_reference_values(value)
            elif value := message_value.get("complex", {}):
                return self.handle_transformers_and_filters(value)
        return []

    def handle_script_arguments(self, script_arguments: dict) -> list[str]:
        """
        Check that When referencing a context value, it is valid, i.e. iscontext: true or surrounded by ${<condition>},
        in a script arguments section.
        Returns: True if the references are correct
        """
        if arg_value := script_arguments.get("simple"):
            return self.get_invalid_reference_values(arg_value)
        elif arg_value := script_arguments.get("complex", {}):
            return self.handle_transformers_and_filters(arg_value)
        
