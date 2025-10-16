from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects import (
    AgentixAction,
)
from demisto_sdk.commands.content_graph.objects.agentix_action import (
    AgentixActionArgument,
    AgentixActionOutput,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction

args_valid_types = [
    "unknown",
    "keyValue",
    "textArea",
    "string",
    "number",
    "date",
    "boolean",
]

outputs_valid_types = ["unknown", "string", "number", "date", "boolean", "json"]


class IsTypeValid(BaseValidator[ContentTypes]):
    error_code = "AG105"
    description = "Ensures that all arguments and outputs use valid data types from the closed list."
    rationale = "Helps the LLM understand and process data correctly according to its expected type."
    error_message = "The following Agentix action '{0}' contains invalid types:\n{1}"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            final_message = ""

            # Check invalid arguments types
            if invalid_args_types := self.is_invalid_args_type(
                content_item.args, args_valid_types
            ):
                final_message += (
                    f"Arguments with invalid types: {', '.join(invalid_args_types)}. "
                    f"Possible argument types: {', '.join(args_valid_types)}.\n"
                )

            # Check invalid outputs types
            if invalid_outputs_types := self.is_invalid_outputs_type(
                content_item.outputs, outputs_valid_types
            ):
                final_message += (
                    f"Outputs with invalid types: {', '.join(invalid_outputs_types)}. "
                    f"Possible output types: {', '.join(outputs_valid_types)}."
                )

            if final_message:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.display_name,
                            final_message,
                        ),
                        content_object=content_item,
                    )
                )

        return validation_results

    def is_invalid_args_type(
        self,
        elements: Optional[List[AgentixActionArgument]],
        valid_types: List[str],
    ) -> Set[str]:
        invalid_element_names: Set[str] = set()
        if elements is None:
            return invalid_element_names

        for element in elements:
            if element.type.lower() not in valid_types:
                invalid_element_names.add(element.name)

        return invalid_element_names

    def is_invalid_outputs_type(
        self,
        elements: Optional[List[AgentixActionOutput]],
        valid_types: List[str],
    ) -> Set[str]:
        invalid_element_names: Set[str] = set()
        if elements is None:
            return invalid_element_names

        for element in elements:
            if element.type.lower() not in valid_types:
                invalid_element_names.add(element.name)

        return invalid_element_names
