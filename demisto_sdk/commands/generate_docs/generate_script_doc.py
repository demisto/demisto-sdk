import os
import random
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_from_version,
    get_relative_path_from_packs_dir,
    get_yaml,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects import Script
from demisto_sdk.commands.generate_docs.common import (
    build_example_dict,
    generate_list_section,
    generate_numbered_section,
    generate_section,
    generate_table_section,
    save_output,
    string_escape_md,
)


def generate_script_doc(
    input_path,
    examples,
    output: str = None,
    permissions: str = None,
    limitations: str = None,
    insecure: bool = False,
    use_graph: bool = True,
):
    try:
        doc: list = []
        errors: list = []
        example_section: list = []

        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input_path))

        if examples:
            if Path(examples).is_file():
                with open(examples) as examples_file:
                    examples = examples_file.read().splitlines()
            else:
                examples = examples.split(",")
                for i, example in enumerate(examples):
                    if not example.startswith("!"):
                        examples[i] = f"!{examples}"

            example_dict, build_errors = build_example_dict(examples, insecure)
            script_name = list(example_dict.keys())[0] if example_dict else None
            example_section, example_errors = generate_script_example(
                script_name, example_dict
            )
            errors.extend(build_errors)
            errors.extend(example_errors)
        else:
            errors.append(
                "Note: Script example was not provided. For a more complete documentation,run with the -e "
                'option with an example command. For example: -e "!ConvertFile entry_id=\\<entry_id>".'
            )

        script = get_yaml(input_path)

        # get script data
        script_info = get_script_info(input_path)

        # get script dependencies
        dependencies: List = []
        used_in: List = []
        if use_graph:
            with ContentGraphInterface() as graph:
                update_content_graph(
                    graph,
                    use_git=True,
                    output_path=graph.output_path,
                )
                result = graph.search(path=get_relative_path_from_packs_dir(input_path))
                if not isinstance(result, List) or result == []:
                    logger.error(
                        f"The requested script {input_path} wasn't found in the graph."
                    )
                else:
                    script_object = result[0]
                    if not isinstance(script_object, Script):
                        logger.error(
                            "The object returned from the graph isn't a script."
                        )
                    else:
                        used_in.extend(
                            relationship.content_item_to.object_id
                            for relationship in script_object.used_by
                        )
                        dependencies.extend(
                            relationship.content_item_to.object_id
                            for relationship in script_object.uses
                        )
        else:
            logger.info(
                f"Skipping fetching dependencies and used_in for the script {input_path} "
                f"as the no-graph argument was given."
            )

        description = script.get("comment", "")
        # get inputs/outputs
        inputs, inputs_errors = get_inputs(script)
        outputs, outputs_errors = get_outputs(script)

        errors.extend(inputs_errors)
        errors.extend(outputs_errors)

        if not description:
            errors.append("Error! You are missing a description for the Script")

        doc.append(description + "\n")

        doc.extend(generate_table_section(script_info, "Script Data"))

        if dependencies:
            doc.extend(
                generate_list_section(
                    "Dependencies",
                    sorted(dependencies),
                    True,
                    text="This script uses the following commands and scripts.",
                )
            )

        # Script global permissions
        if permissions == "general":
            doc.extend(generate_section("Permissions", ""))

        if used_in:
            if len(used_in) <= 10:
                doc.extend(
                    generate_list_section(
                        "Used In",
                        used_in,
                        True,
                        text="This script is used in the following playbooks and scripts.",
                    )
                )
            else:  # if we have more than 10 use a sample
                logger.info(
                    f'<yellow>"Used In" section found too many scripts/playbooks ({len(used_in)}). Will use a sample of 10.'
                    " Full list is available as a comment in the README file.</yellow>"
                )
                sample_used_in = random.sample(used_in, 10)
                doc.extend(
                    generate_list_section(
                        "Used In",
                        sorted(sample_used_in),
                        True,
                        text="Sample usage of this script can be found in the following playbooks and scripts.",
                    )
                )
                used_in_str = "\n".join(used_in)
                doc.append(
                    f"<!--\nUsed In: list was truncated. Full list commented out for reference:\n\n{used_in_str}\n -->\n"
                )

        doc.extend(
            generate_table_section(
                inputs, "Inputs", "There are no inputs for this script."
            )
        )

        doc.extend(
            generate_table_section(
                outputs, "Outputs", "There are no outputs for this script."
            )
        )

        if example_section:
            doc.extend(example_section)

        # Known limitations
        if limitations:
            doc.extend(generate_numbered_section("Known Limitations", limitations))

        doc_text = "\n".join(doc)
        if not doc_text.endswith("\n"):
            doc_text += "\n"

        save_output(output, "README.md", doc_text)

        if errors:
            logger.info("<yellow>Possible Errors:</yellow>")
            for error in errors:
                logger.info(f"<yellow>{error}</yellow>")

    except Exception as ex:
        logger.info(f"<yellow>Error: {str(ex)}</yellow>")
        return


def get_script_info(script_path: str, clear_cache: bool = False):
    """
    Gets script information(type, tags, docker image and demisto version).
    :param script_path: the script yml file path.
    :param clear_cache: whether to clear cache before getting yml.
    :return: list of dicts contains the script information.
    """
    script = get_yaml(script_path, cache_clear=clear_cache)
    script_type = script.get("subtype")
    if not script_type:
        script_type = script.get("type")

    tags = script.get("tags", [])
    tags = ", ".join(map(str, tags))

    from_version = get_from_version(script_path)
    res = []
    if script_type:
        res.append({"Name": "Script Type", "Description": script_type})
    if tags:
        res.append({"Name": "Tags", "Description": tags})
    if from_version != "":
        res.append({"Name": "Cortex XSOAR Version", "Description": from_version})
    return res


def get_inputs(script):
    """
    Gets script inputs.
    :param script: the script object.
    :return: list of inputs and list of errors.
    """
    errors = []
    inputs = []

    if not script.get("args"):
        return {}, []

    for arg in script.get("args"):
        if not arg.get("description"):
            errors.append(
                "Error! You are missing description in script input {}".format(
                    arg.get("name")
                )
            )

        inputs.append(
            {
                "Argument Name": arg.get("name"),
                "Description": string_escape_md(
                    arg.get("description", ""), escape_html=False
                ),
            }
        )

    return inputs, errors


def get_outputs(script):
    """
    Gets script outputs.
    :param script: the script object.
    :return: list of outputs and list of errors.
    """
    errors = []
    outputs = []

    if not script.get("outputs"):
        return {}, []

    for arg in script.get("outputs"):
        if not arg.get("description"):
            errors.append(
                "Error! You are missing description in script output {}".format(
                    arg.get("contextPath")
                )
            )

        outputs.append(
            {
                "Path": arg.get("contextPath"),
                "Description": string_escape_md(
                    arg.get("description", ""), escape_html=False
                ),
                "Type": arg.get("type", "Unknown"),
            }
        )

    return outputs, errors


def generate_script_example(script_name, example=None):
    results = []
    errors = []
    if not example:
        errors.append(
            f"did not get any example for {script_name}. please add it manually."
        )
    else:
        examples = example.get(script_name, None)
        if not examples:
            return "", [
                f"did not get any example for {script_name}. please add it manually."
            ]
        results.extend(["## Script Examples", ""])
        for script_example, md_example, context_example in examples:
            results.extend(["### Example command", "", f"```{script_example}```"])
            if context_example:
                results.extend(
                    [
                        "",
                        "### Context Example",
                        "",
                        "```json",
                        f"{context_example}",
                        "```",
                        "",
                    ]
                )
            if md_example:
                results.extend(
                    [
                        "### Human Readable Output",
                        "{}".format(">".join(f"\n{md_example}".splitlines(True))),
                        # prefix human readable with quote
                        "",
                    ]
                )

    return results, errors
