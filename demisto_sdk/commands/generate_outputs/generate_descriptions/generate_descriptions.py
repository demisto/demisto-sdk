import itertools
import math
import os
import os.path
import threading
import time
from typing import Dict

import requests

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_yaml, write_dict

CREDENTIALS = 9

old_merge_environment_settings = requests.Session.merge_environment_settings

# Globals
STOP_SEQS = ["\n", "\ncontextPath:"]

# The base instructions for the GPT model, this is how it knows that we want it
# to do. How the structure of the response looks and what it should look like.
CURRENT_PROMPT = [
    "contextPath: Guardicore.Incident.source_asset.labels\ndescriptionMessage: The source assets labels for the Incident.",
    "contextPath: Something.Incident.reenrich_count\ndescriptionMessage: The number of re-enrichments made on an incident.",
    "contextPath: VeryBigWord.Endpoint.vm.orchestration_details.orchestration_obj_id\n"
    + "descriptionMessage: The orchestration object identifier for an Endpoint's virtual machine.",
    "contextPath: AAA.Endpoint.status\ndescriptionMessage: The status of an Endpoint (off/on).",
    "contextPath: DDDdddRRR.Endpoint.is_on_alert\ndescriptionMessage: Whether the endpoint is on or not.",
    "contextPath: Blabla.Endpoint.active\ndescriptionMessage: Whether the endpoint is on or off.",
    "contextPath: Guardicore.Endpoint.nics.is_cloud_public\ndescriptionMessage: Whether the Endpoint's NIC is in the public cloud or not.",
    "contextPath: Activity.Endpoint.active\ndescriptionMessage: Whether the Endpoint is on or off.",
    "contextPath: IDID.Endpoint.host_orchestration_id\ndescriptionMessage: The orchestration object identifier for the Endpoint's host.",
    "contextPath: BrublaBRO.Endpoint.is_on\ndescriptionMessage:  Whether the Endpoint is on or not.",
    "contextPath: WellDone.Endpoint.metadata.InventoryAPI.report_source\ndescriptionMessage:  The Endpoint's InvestoryAPI report source.",
]
PROMPT_HISTORY = CURRENT_PROMPT[::]
PROMPT_MAX_LINES = 40
LOADING_DONE = False
INPUT_PREFIX = ">> Generated output: \t"
DEBUG_PROMPT = True


def pinput(prompt, prefill=""):
    """Interactive input with a prefix"""
    import readline

    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()


def remove_last_prompt():
    """When the prompt is too big we need to clear it."""
    global CURRENT_PROMPT

    if len(CURRENT_PROMPT) >= PROMPT_MAX_LINES:
        logger.debug(f"Prompt too big (>{PROMPT_MAX_LINES}) sliding window")
        CURRENT_PROMPT.pop(0)


def correct_prompt(ctx, correct_desc):
    """Correct the currently usee prompt with new
    user corrected descriptions"""
    global CURRENT_PROMPT, PROMPT_HISTORY
    remove_last_prompt()
    CURRENT_PROMPT.append(f"contextPath: {ctx}\ndescriptionMessage: {correct_desc}")
    PROMPT_HISTORY.append(CURRENT_PROMPT[-1])


def get_current_prompt():
    global CURRENT_PROMPT
    return "\n".join(CURRENT_PROMPT)


def animate():
    """Show a nice animation spinner"""
    global LOADING_DONE
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        if LOADING_DONE:
            break
        logger.info(f"\r{INPUT_PREFIX} {c}")
        time.sleep(0.1)


def generate_desc_with_spinner(command_output_path, insecure, output):
    global LOADING_DONE
    LOADING_DONE = False
    t = threading.Thread(target=animate)
    t.start()
    output = generate_desc(command_output_path, prob_check=True, insecure=insecure)
    LOADING_DONE = True
    return output


def generate_desc(input_ctx, prob_check=False, insecure=False):
    # from demisto_sdk.commands.common.loguru_logger import logger
    # logger.setLevel(logging.ERROR)

    prompt = get_current_prompt()
    prompt += f"contextPath: {input_ctx}\ndescriptionMessage:"

    return ai21_api_request(prompt, {"prob_check": prob_check, "insecure": insecure})


def ai21_api_request(prompt, options={}):
    ai21_key = os.environ.get("AI21_KEY")
    if not ai21_key:
        logger.info("<red>No ai21 key provided, see docs and obtain one.</red>")
        return

    res = requests.post(
        "https://api.ai21.com/studio/v1/j1-large/complete",
        headers={"Authorization": f"Bearer {ai21_key}"},
        json={
            "prompt": prompt,
            "numResults": 1,
            "maxTokens": 8,
            "stopSequences": STOP_SEQS,
            "topKReturn": 0,
            "temperature": 0.0,
        },
        verify=options.get("insecure", False),
    )

    data = res.json().get("completions")[0].get("data")
    output = data.get("text")
    prob_check = options.get("prob_check", False)

    if prob_check:
        output = build_description_with_probabilities(data)
    return output.strip()


def build_description_with_probabilities(data):
    """Build the description and wrap low probabilities with *'s"""
    output = ""
    probability_threashold = 0.2  # less than 20% sure, higher is more precise.
    tokens = data.get("tokens")
    for token in tokens:
        token = token.get("generatedToken")
        i = token.get("token").replace("▁", " ").replace("<|newline|>", "")
        v = token.get("logprob")
        if i in STOP_SEQS:
            break
        v = math.exp(v)

        # Wrap low probability tokens with **'s
        if v < probability_threashold:
            output += f" **{i.lstrip()}**"
        else:
            output += i
    return output


def write_desc(c_index, final_output, o_index, output_path, yml_data):
    """Write a description to disk"""
    logger.debug(f"Writing: {final_output}\n---")
    yml_data["script"]["commands"][c_index]["outputs"][o_index]["description"] = (
        final_output
    )
    write_dict(output_path, yml_data)


def correct_interactively(command_output_path, final_output, output):
    logger.info("\r")
    final_output = pinput(INPUT_PREFIX, final_output)

    # Learn from mistakes
    if final_output != output:
        y = input("Should we append to prompt (y/n)? ").lower()
        if y == "y" or y == "yes":
            logger.info(f"(Correcting prompt `{final_output}` instead of `{output}`)")
            correct_prompt(command_output_path, final_output)
    return final_output


def print_experimental():
    logger.info("\n")
    logger.info("⚠" * 100)
    logger.info(
        """    ███████ ██   ██ ██████  ███████ ██████  ██ ███    ███ ███████ ███    ██ ████████  █████  ██
    ██       ██ ██  ██   ██ ██      ██   ██ ██ ████  ████ ██      ████   ██    ██    ██   ██ ██
    █████     ███   ██████  █████   ██████  ██ ██ ████ ██ █████   ██ ██  ██    ██    ███████ ██
    ██       ██ ██  ██      ██      ██   ██ ██ ██  ██  ██ ██      ██  ██ ██    ██    ██   ██ ██
    ███████ ██   ██ ██      ███████ ██   ██ ██ ██      ██ ███████ ██   ████    ██    ██   ██ ███████
    """
    )
    logger.info("this feature is experimental, use with caution.")
    logger.info("⚠" * 100)
    logger.info("\n")


def generate_ai_descriptions(
    input_path: str,
    output_path: str = "out.yml",
    interactive: bool = True,
    insecure: bool = False,
):
    """Generate integration command contexts.

    Args:
        input_path: path to the yaml integration input path
        output_path: path to the yaml integration output path
        interactive: interactivity (correct ai result mistakes)
        insecure: insecure https (debug mode)
    """
    print_experimental()

    try:
        similar_paths: Dict[str, str] = {}
        yml_data = get_yaml(input_path)

        # Fix sometimes the yml doesn't contain the full structure
        #  (json-to-outputs)
        if "script" not in yml_data:
            yml_data = {"script": {"commands": [yml_data]}}

        commands = yml_data.get("script", {})
        commands = commands.get("commands", [])

        # Iterate over every command
        for c_index, command in enumerate(commands):
            command_name = command.get("name")

            if interactive:
                logger.debug(f"Command: {command_name}")

            outputs = command.get("outputs")
            if not outputs:
                if interactive:
                    logger.debug("-- Skipping because no outputs for command")
                continue

            # Iterate over every output per command
            for o_index, o in enumerate(outputs):
                command_output_path = o.get("contextPath")

                # Match past paths automatically.
                if command_output_path in similar_paths:
                    logger.info(
                        f"\n--Already added description for exact path: {command_output_path}--"
                    )
                    final_output = similar_paths.get(command_output_path)
                    logger.info(f"Last output was: '{final_output}'")
                    y = input("Should we use it (y/n)? ").lower()
                    if y == "y" or y == "yes":
                        logger.info("Using last seen output.")
                        yml_data["script"]["commands"][c_index]["outputs"][o_index][
                            "description"
                        ] = final_output
                        write_dict(output_path, yml_data)
                        continue
                    else:
                        logger.info("Asking again...")

                # Print the progress and current context path
                if interactive:
                    logger.debug(f"\n{o_index + 1}/{len(outputs)}")
                    logger.debug(f"Command: {command_name}")
                    logger.debug(f"Context path:\t\t{command_output_path}")

                output = "No result from GPT."

                # Generate a description with AI21 API (retry twice in case we
                # have a long prompt we need to clear).
                for _exception in range(2):
                    try:
                        output = generate_desc_with_spinner(
                            command_output_path, insecure, output
                        )
                        break
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed AI description request: {e}")
                        remove_last_prompt()
                        continue

                final_output = output

                # Correct the description if needed interactively
                if interactive:
                    final_output = correct_interactively(
                        command_output_path, final_output, output
                    )

                # Write the final description to the file (backup)
                write_desc(c_index, final_output, o_index, output_path, yml_data)

                # Update the similar context paths
                similar_paths[command_output_path] = str(final_output)

            # Backup the prompt for later usage (in case we cleared the prompt)
            if DEBUG_PROMPT:
                with open(f"backup_prompt_ai_{c_index}.txt", "w") as f:
                    f.write(get_current_prompt())

    except Exception as ex:
        logger.info(f"<red>Error: {str(ex)}</red>")

    # backup all of the prompts (without truncating)
    if DEBUG_PROMPT:
        with open("history_prompt.txt", "w") as f:
            f.write(json.dumps(PROMPT_HISTORY))
