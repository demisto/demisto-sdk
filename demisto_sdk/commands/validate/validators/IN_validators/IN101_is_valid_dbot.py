from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.common.constants import (
    DBOT_SCORES_DICT,
    REPUTATION_COMMAND_NAMES,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDbotValidator(BaseValidator[ContentTypes]):
    error_code = "IN101"
    description = "Outputs of reputation commands must adhere to standards."
    rationale = "Uniform outputs allow creating generic content. For more information, see https://xsoar.pan.dev/docs/integrations/generic-commands-reputation"
    error_message = "The integration contains reputation command(s) with missing outputs/malformed descriptions:{0}"
    related_field = "outputs"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.create_error_message_str(malformed_commands)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                malformed_commands := self.get_malformed_reputation_commands(
                    content_item.commands
                )
            )
        ]

    def get_malformed_reputation_commands(
        self, commands: List[Command]
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        malformed_commands: Dict[str, Dict[str, Dict[str, str]]] = {}
        for command in commands:
            if command.name in REPUTATION_COMMAND_NAMES:
                missing_outputs: Dict[str, str] = {}
                malformed_description: Dict[str, str] = {}
                reputation_command_outputs = {
                    output.contextPath: output.description for output in command.outputs
                }
                for context_path, description in DBOT_SCORES_DICT.items():
                    if context_path not in reputation_command_outputs:
                        missing_outputs[context_path] = description
                    elif reputation_command_outputs[context_path] != description:
                        malformed_description[context_path] = description
                if missing_outputs or malformed_description:
                    malformed_commands[command.name] = {
                        "missing_outputs": missing_outputs,
                        "malformed_description": malformed_description,
                    }
        return malformed_commands

    def create_error_message_str(
        self, results: Dict[str, Dict[str, Dict[str, str]]]
    ) -> str:
        result_str: str = ""
        for command_name, issues in results.items():
            result_str = f"{result_str}\nThe command '{command_name}' is invalid:"
            if missing_outputs := issues.get("missing_outputs"):
                formatted_missing_outputs = "\n".join(
                    [
                        f"\t\t- The output '{missing_output}', the description should be '{missing_output_description}'"
                        for missing_output, missing_output_description in missing_outputs.items()  # type: ignore[attr-defined]
                    ]
                )
                result_str = f"{result_str}\n\tThe following outputs are missing:\n{formatted_missing_outputs}"
            if outputs_with_malformed_descriptions := issues.get(
                "malformed_description"
            ):
                formatted_malformed_descriptions = "\n".join(
                    [
                        f"\t\t- The output '{output}' description is invalid. Description should be '{expected_description}'"
                        for output, expected_description in outputs_with_malformed_descriptions.items()  # type: ignore[attr-defined]
                    ]
                )
                result_str = f"{result_str}\n\tThe following outputs descriptions are invalid:\n{formatted_malformed_descriptions}"
        return result_str
