from typing import Dict, List, Optional

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml, write_dict
from demisto_sdk.commands.generate_docs.common import build_example_dict
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    get_command_examples,
)
from demisto_sdk.commands.generate_outputs.json_to_outputs.json_to_outputs import (
    parse_json,
)


def dict_from_outputs_str(command: str, outputs: str):
    """Create a pythonic dict from the yml outputs string.

    Args:
        command: the command to parse.
        outputs: the json outputs to parse into a dict.
    """
    dict_output = parse_json(outputs, command, "", return_object=True)
    return dict_output


def generate_example_dict(examples_file: Optional[str], insecure=False):
    """Generate the example dict via an XSOAR server and return dict results.

    Args:
        examples_file: yaml as python dict.
        insecure: wether to run the examples without checking ssl.
    """
    command_examples = get_command_examples(examples_file, None)
    example_dict, build_errors = build_example_dict(command_examples, insecure)
    if build_errors:
        raise Exception(f"Command examples had errors: {build_errors}")
    return example_dict


def insert_outputs(yml_data: Dict, command_name: str, output_with_contexts: List):
    """Insert new outputs for a command in the yml_data and return it.

    Args:
        yml_data: yaml as python dict.
        command_name: the command name whose outputs we want to manipulate.
        output_with_contexts: the new outputs.
    """
    commands = yml_data.get("script", {}).get("commands") or []
    command_names = [command.get("name") for command in commands]
    if command_name not in command_names:
        raise ValueError(
            f"The {command_name} command is missing from the integration YML."
        )
    command_index = command_names.index(command_name)
    command = commands[command_index]

    outputs: List[Dict[str, str]] = command.get("outputs") or []
    old_descriptions = _output_path_to_description(outputs)
    new_descriptions = _output_path_to_description(output_with_contexts)
    old_output_paths = {
        output.get("contextPath") for output in command.get("outputs", [])
    }

    outputs.extend(
        output
        for output in output_with_contexts
        if output.get("contextPath")
        and output.get("contextPath") not in old_output_paths
    )

    # populates the description field, preferring the new value (if not blank), and existing values over blanks.
    for output in outputs:
        path = output.get("contextPath")
        if not path:
            raise ValueError("Found a command without a contextPath value")
        if not output.get("description"):
            output["description"] = (
                new_descriptions.get(path) or old_descriptions.get(path) or ""
            )
    yml_data["script"]["commands"][command_index]["outputs"] = outputs
    return yml_data


def _output_path_to_description(
    command_outputs: List[Dict[str, str]],
) -> Dict[str, str]:
    """creates a mapping of contextPath -> description, if the description is not null."""
    descriptions = {}
    for output in command_outputs:
        description = output.get("description")
        context_path = output.get("contextPath")
        if context_path and description:
            descriptions[context_path] = description
    return descriptions


def generate_integration_context(
    input_path: str,
    examples: Optional[str] = None,
    insecure: bool = False,
    output_path: Optional[str] = None,
):
    """Generate integration command contexts in-place.

    Args:
        output_path: Output path
        input_path: path to the yaml integration.
        examples: path to the command examples.
        insecure: should use insecure.
    """
    if not output_path:
        output_path = input_path
    try:
        yml_data = get_yaml(input_path)

        # Parse examples file
        example_dict = generate_example_dict(examples, insecure)

        for command in example_dict:
            logger.debug(f"Building context for the {command} command...")
            example = example_dict.get(command)

            # Generate the examples with a local server
            for _, _, outputs in example:
                output_with_contexts = dict_from_outputs_str(command, outputs)
                output_contexts = output_with_contexts.get("outputs")
                yml_data = insert_outputs(yml_data, command, output_contexts)

        # Make the changes in place the input yml
        logger.info(f"<green>Writing outputs to {output_path}</green>")
        write_dict(output_path, yml_data)
    except ValueError as ex:
        logger.info(f"<red>Error: {str(ex)}</red>")
        return 1
    return 0
