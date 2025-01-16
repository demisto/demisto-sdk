from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from demisto_sdk.commands.content_graph.objects.base_playbook import Task, TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsCorrectValueReferencesInterface(BaseValidator[ContentTypes]):
    error_code = "PB121"
    description = "Validate that all inputs that are intended to be fetched from the context are correctly notated."
    rationale = "Context paths can be mistakenly used without the correct notation."
    error_message = (
        "In task: '{task_name}' with ID: '{task_id}', an input with the value: '{path}' was passed as a string not a reference."
        ' Change the reference to "From previous tasks" from "As value", or change the value to ${{{path}}}.'
    )
    related_field = "conditions"
    is_auto_fixable = True
    fix_message = "Fixed the following inputs:\n"
    handle_value_obj: Callable = lambda x: x

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> list[ValidationResult]:
        """Check that references of context values, are valid, i.e. "iscontext: true" or surrounded by ${<condition>},
        Args:
            content_items (Iterable[ContentTypes]): The content items to check.
        Returns:
            List[ValidationResult]. List of ValidationResults objects.
        """
        self.handle_value_obj = self.get_invalid_value_obj

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    task_id=task.id,
                    task_name=task.task.name,
                    path=value,
                ),
                content_object=playbook,
            )
            for playbook in content_items
            for task, value in self.get_invalid_playbook_inputs(playbook)
        ]

    def get_invalid_playbook_inputs(
        self, playbook: ContentTypes
    ) -> list[tuple[TaskConfig, str]]:
        """Get invalid playbook inputs based on the task type."""

        results: list[tuple[TaskConfig, str]] = []

        for task in playbook.tasks.values():
            is_task_valid = {
                "condition": self.get_invalid_condition_task,
                "regular": self.get_invalid_regular_task,
                "collection": self.get_invalid_data_collection_task,
            }.get(task.type, lambda _: [])  # type: ignore

            invalid_values = (
                is_task_valid(task)
                + self.handle_value_obj(task.task, "description")
                + self.handle_value_obj(task.task, "name")
            )

            results += [(task, val) for val in invalid_values]

        return results

    def get_invalid_condition_task(self, task: TaskConfig) -> list[str]:
        """Get the invalid inputs in a condition task."""
        task.task.description
        invalid_values = []
        for conditions in task.conditions or []:
            for condition in conditions.get("condition", []):
                for condition_info in condition:
                    invalid_values += self.handle_op_arg(
                        **condition_info.get("left", {})
                    ) + self.handle_op_arg(**condition_info.get("right", {}))
        for message_key, message_value in (task.message or {}).items():
            invalid_values += self.get_invalid_message_values(
                message_key, message_value
            )
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_input_obj(script_argument)
        return invalid_values

    def get_invalid_regular_task(self, task: TaskConfig) -> list[str]:
        """Get the invalid inputs in a regular task."""
        invalid_values = []
        invalid_values += self.handle_input_obj(task.defaultassigneecomplex)
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_input_obj(script_argument)
        for incident_field in task.fieldMapping or []:
            invalid_values += self.handle_input_obj(incident_field.get("output"))
        return invalid_values

    def get_invalid_data_collection_task(self, task: TaskConfig) -> list[str]:
        """Get the invalid inputs in a data collection task."""
        invalid_values = []
        for script_argument in (task.scriptarguments or {}).values():
            invalid_values += self.handle_input_obj(script_argument)
        for message_key, message_value in (task.message or {}).items():
            invalid_values += self.get_invalid_message_values(
                message_key, message_value
            )
        for form_question in (task.form or {}).get("questions", []):
            if labelarg := form_question.get("labelarg", {}):
                invalid_values += self.handle_input_obj(labelarg)
        return invalid_values

    def handle_transformers_and_filters(self, field_output: dict) -> list[str]:
        """Get the invalid inputs in an input with transformers and filters."""
        invalid_values = []
        for incident_filter in field_output.get("filters", []):
            for filter_info in incident_filter:
                invalid_values += self.handle_op_arg(
                    **filter_info.get("left", {})
                ) + self.handle_op_arg(**filter_info.get("right", {}))
        for transformer in field_output.get("transformers", []):
            for arg_info in transformer.get("args", {}).values():
                invalid_values += self.handle_op_arg(**(arg_info or {}))
        return invalid_values

    @staticmethod
    def get_invalid_reference_values(values: Any) -> list[str]:
        """Get the invalid inputs in an input string."""
        return (
            [
                value
                for value in values.split(",")
                if value.startswith("incident.") or value.startswith("inputs.")
            ]
            if isinstance(values, str)
            else []
        )

    def get_invalid_message_values(self, message_key, message_value) -> list[str]:
        """Get the invalid inputs from message values."""
        if message_key and message_value and isinstance(message_value, dict):
            return self.handle_input_obj(message_value)
        return []

    def handle_op_arg(
        self, value: Optional[dict] = {}, iscontext: bool = False, **_
    ) -> list[str]:
        """Get the invalid inputs in an operation argument."""
        return self.handle_input_obj(value, iscontext)

    def handle_input_obj(
        self, value_obj: Optional[dict], is_context: bool = False
    ) -> list[str]:
        """Get the invalid inputs from an input object."""
        if not is_context:
            value_obj = value_obj or {}
            if "simple" in value_obj:
                return self.handle_value_obj(value_obj)
            elif arg_value := value_obj.get("complex", {}):
                return self.handle_transformers_and_filters(arg_value)
        return []

    def get_invalid_value_obj(self, value_obj: dict, key: str = "simple") -> list[str]:
        """Alternate for handle_value_obj(), used in get_invalid_content_items()"""
        if isinstance(value_obj, dict):
            return self.get_invalid_reference_values(value_obj.get(key))
        return self.get_invalid_reference_values(getattr(value_obj, key, None))

    def fix_value_obj(self, value_obj: dict | Task, key: str = "simple") -> list[str]:
        """Alternate for handle_value_obj(), used in fix()"""
        invalid_values = []
        if isinstance(value_obj, dict):
            if value := value_obj.get(key):
                invalid_values = self.get_invalid_reference_values(value)
                for inv in invalid_values:
                    value = value.replace(inv, f"${{{inv}}}")
                value_obj[key] = value
        elif value := getattr(value_obj, key, None):
            invalid_values = self.get_invalid_reference_values(value)
            for inv in invalid_values:
                value = value.replace(inv, f"${{{inv}}}")
            setattr(value_obj, key, value)
        return invalid_values

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Adds the "${}" syntax to all invalid inputs.

        Args:
            content_item (ContentTypes): The content item to fix.

        Returns:
            FixResult: The result of the fix operation.
        """

        self.handle_value_obj = self.fix_value_obj

        invalid_values = self.get_invalid_playbook_inputs(content_item)

        return FixResult(
            validator=self,
            message=self.fix_message
            + "\n".join(
                f"'{val}' in task: '{task.task.name}'" for task, val in invalid_values
            ),
            content_object=content_item,
        )
