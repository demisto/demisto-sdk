from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List, Union

from demisto_sdk.commands.common.constants import VALID_SENTENCE_SUFFIX
from demisto_sdk.commands.common.tools import is_string_ends_with_url
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class DescriptionEndsWithDotValidator(BaseValidator[ContentTypes]):
    error_code = "DS108"
    description = "Ensure that all yml's description fields ends with a dot."
    rationale = "To ensure high documentation standards."
    error_message = "The {0} contains description fields without dots at the end:{1}\nPlease make sure to add a dot at the end of all the mentioned fields."
    fix_message = "Added dots ('.') at the end of the following description fields:{0}"
    related_field = "description, comment"
    is_auto_fixable = True
    lines_without_dots: ClassVar[Dict[str, dict]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            self.lines_without_dots[content_item.name] = {}
            lines_with_missing_dot: str = ""
            if (
                stripped_description := strip_description(
                    content_item.description or ""
                )
            ) and is_invalid_description_sentence(stripped_description):
                self.lines_without_dots[content_item.name]["description"] = (
                    f"{stripped_description}."
                )
                lines_with_missing_dot = f"{lines_with_missing_dot}\nThe file's {'comment' if isinstance(content_item, Script) else 'description'} field is missing a '.' at the end of the sentence."
            lines_with_missing_dot_dict: Dict[str, List[str]] = {}
            if isinstance(content_item, Script):
                if args_and_context_lines_with_missing_dot := is_line_ends_with_dot(
                    content_item, lines_with_missing_dot_dict
                ):
                    lines_with_missing_dot = f"{lines_with_missing_dot}\n{args_and_context_lines_with_missing_dot}"
                    self.lines_without_dots[content_item.name] = (
                        lines_with_missing_dot_dict
                    )
            else:
                for command in content_item.commands:
                    if current_command := is_line_ends_with_dot(
                        command, lines_with_missing_dot_dict, "\n\t"
                    ):
                        lines_with_missing_dot += (
                            f"\n- In command '{command.name}':{current_command}"
                        )
                        self.lines_without_dots[content_item.name][command.name] = (
                            lines_with_missing_dot_dict
                        )
                        lines_with_missing_dot_dict = {}
            if lines_with_missing_dot:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.content_type, lines_with_missing_dot
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        fix_message: str = ""
        content_item_malformed_lines = self.lines_without_dots[content_item.name]
        if "description" in content_item_malformed_lines:
            content_item.description = f"{content_item.description}."
            fix_message = f"\nAdded a '.' at the end of the {'comment' if isinstance(content_item, Script) else 'description'} field."
        if isinstance(content_item, Script):
            if malformed_args := content_item_malformed_lines.get("args", []):
                for arg in content_item.args:
                    if arg.name in malformed_args:
                        arg.description = f"{arg.description}."
                        fix_message = f"{fix_message}\nAdded a '.' at the end of the argument '{arg.name}' description field."
            if malformed_context_paths := content_item_malformed_lines.get(
                "contextPath", []
            ):
                for output in content_item.outputs:
                    if output.contextPath in malformed_context_paths:
                        output.description = f"{output.description}."
                        fix_message = f"{fix_message}\nAdded a '.' at the end of the output '{output.contextPath}' description field."
        else:
            for command in content_item.commands:
                command_fix_msg = ""
                if command.name in content_item_malformed_lines:
                    command_malformed_args = content_item_malformed_lines[command.name][
                        "args"
                    ]
                    command_malformed_context_paths = content_item_malformed_lines[
                        command.name
                    ]["contextPath"]
                    for arg in command.args:
                        if arg.name in command_malformed_args:
                            arg.description = f"{arg.description}."
                            command_fix_msg = f"{command_fix_msg}\n\tAdded a '.' at the end of the argument '{arg.name}' description field."
                    for output in command.outputs:
                        if output.contextPath in command_malformed_context_paths:
                            output.description = f"{output.description}."
                            command_fix_msg = f"{command_fix_msg}\n\tAdded a '.' at the end of the output '{output.contextPath}' description field."
                    if command_fix_msg:
                        fix_message = f"{fix_message}\n In the command {command.name}:{command_fix_msg}"
        return FixResult(
            validator=self,
            message=self.fix_message.format(fix_message),
            content_object=content_item,
        )


def strip_description(description: str):
    """
    Args:
        description: a description string.
    Returns: the description stripped from quotes mark if they appear both in the beginning and in the end of the string.
    """
    description = description.strip()
    return (
        description.strip('"')
        if description.startswith('"') and description.endswith('"')
        else description.strip("'")
        if description.startswith("'") and description.endswith("'")
        else description
    )


def is_invalid_description_sentence(stripped_description: str) -> bool:
    """
    Args:
        stripped_description: (str) a description or comment section from script / integration yml.
    Return True (the description string is invalid) if all of the following conditions are met:
    - The description string exist and not empty.
    - The description string doesn't end with a dot, question mark or exclamation mark.
    - The description string doesn't end with an URL.
    - The description string doesn't end with a dot inside brackets or quote.
    """
    return all(
        [
            stripped_description,
            not any(
                [
                    stripped_description.endswith(suffix)
                    for suffix in VALID_SENTENCE_SUFFIX
                ]
            ),
            not is_string_ends_with_url(stripped_description),
        ]
    )


def is_line_ends_with_dot(
    obj_to_test: Command | Script,
    lines_with_missing_dot_dict: Dict[str, List[str]],
    line_separator: str = "\n",
):
    line_with_missing_dot: str = ""
    args_with_missing_dots: List[str] = []
    context_path_with_missing_dots: List[str] = []
    for arg in obj_to_test.args:
        stripped_description = strip_description(arg.description)
        if is_invalid_description_sentence(stripped_description):
            line_with_missing_dot += f"{line_separator}The argument {arg.name} description should end with a period."
            args_with_missing_dots.append(arg.name)
    for output in obj_to_test.outputs:
        stripped_description = strip_description(output.description or "")
        if is_invalid_description_sentence(stripped_description):
            line_with_missing_dot += f"{line_separator}The context path {output.contextPath} description should end with a period."
            context_path_with_missing_dots.append(output.contextPath)  # type: ignore[arg-type]
    lines_with_missing_dot_dict["args"] = args_with_missing_dots
    lines_with_missing_dot_dict["contextPath"] = context_path_with_missing_dots

    return line_with_missing_dot
