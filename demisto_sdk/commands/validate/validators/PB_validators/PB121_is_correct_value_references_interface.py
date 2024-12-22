from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
    FixResult
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
        ' Change the reference to "From previous tasks" from "As value", or change the value to ${{{path}}}.'
    )
    related_field = "conditions"
    is_auto_fixable = True

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
                }.get(task.type, lambda _: [])

                invalid_values = (
                    is_task_valid(task)
                    + self.get_invalid_reference_values(task.task.description or '')
                    + self.get_invalid_reference_values(task.task.name or '')
                )

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
        task.task.description
        invalid_values = []
        for conditions in (task.conditions or []):
            for condition in conditions.get("condition"):
                for condition_info in condition:
                    invalid_values += (
                        self.handle_op_arg(**condition_info.get('left', {}))
                        + self.handle_op_arg(**condition_info.get('right', {}))
                    )
        for message_key, message_value in (task.message or {}).items():
            invalid_values += self.get_invalid_message_values(message_key, message_value)
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_values(script_argument)
        return invalid_values

    def is_valid_regular_task(self, task: TaskConfig) -> list[str]:
        invalid_values = []
        invalid_values += self.handle_values(task.defaultassigneecomplex)
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_values(script_argument)
        for incident_field in (task.fieldMapping or []):
            invalid_values += self.handle_values(incident_field.get("output"))
        return invalid_values

    def is_valid_data_collection(self, task: TaskConfig):
        invalid_values = []
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_values(script_argument)
        for message_key, message_value in (task.message or {}).items():
            invalid_values += self.get_invalid_message_values(message_key, message_value)
        for form_question in (task.form or {}).get("questions", []):
            if labelarg := form_question.get("labelarg", {}):
                invalid_values += self.handle_values(labelarg)
        return invalid_values

    def handle_transformers_and_filters(self, field_output: dict) -> list[str]:
        invalid_values = []
        for incident_filter in field_output.get("filters", []):
            for filter_info in incident_filter:
                invalid_values += (
                    self.handle_op_arg(**filter_info.get('left', {}))
                    + self.handle_op_arg(**filter_info.get('right', {}))
                )
        for transformer in field_output.get("transformers", []):
            for arg_info in transformer.get("args", {}).values():
                invalid_values += self.handle_op_arg(**(arg_info or {}))
        return invalid_values

    @staticmethod
    def get_invalid_reference_values(values: str) -> list[str]:
        return [
            value for value in values.split(",")
            if value.startswith("incident.") or value.startswith("inputs.")
        ]

    def get_invalid_message_values(self, message_key, message_value) -> list[str]:
        if message_key and message_value and isinstance(message_value, dict):
            return self.handle_values(message_value)
        return []
    
    def handle_op_arg(self, value: Optional[dict] = {}, iscontext: bool = False, **_) -> list[str]:
        return self.handle_values(value, iscontext)

    def handle_values(self, value_obj: Optional[dict], is_context: bool = False) -> list[str]:
        if not is_context:
            value_obj = value_obj or {}
            if arg_value := value_obj.get("simple"):
                return self.get_invalid_reference_values(arg_value)
            elif arg_value := value_obj.get("complex", {}):
                return self.handle_transformers_and_filters(arg_value)
        return []
        
    def fix(self, content_item: ContentTypes) -> FixResult:  # TODO
        """
        Sets quietmode to 0 for all tasks with quietmode set to 2 in the given content item.

        Args:
            content_item (ContentTypes): The content item to fix.

        Returns:
            FixResult: The result of the fix operation.
        """
        invalid_tasks = self.invalid_tasks_in_playbooks.get(content_item.name, [])
        for task in invalid_tasks:
            task.quietmode = 0
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                playbook_name=content_item.name,
                tasks=", ".join([task.id for task in invalid_tasks]),
            ),
            content_object=content_item,
        )