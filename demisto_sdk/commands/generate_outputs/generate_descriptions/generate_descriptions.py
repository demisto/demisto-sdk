import itertools
import logging
import math
import os
import os.path
import threading
import time
from typing import Dict

import requests

from demisto_sdk.commands.common.tools import get_yaml, print_error, write_yml

CREDENTIALS = 9

old_merge_environment_settings = requests.Session.merge_environment_settings

logger = logging.getLogger(__name__)


# Globals
STOP_SEQS = ["\n", "\ncontextPath:"]
CURRENT_PROMPT = "contextPath: Guardicore.Incident.source_asset.labels\ndescriptionMessage: The source assets labels for the Incident." \
                 "\ncontextPath: Something.Incident.reenrich_count\ndescriptionMessage: The number of re-enrichments made on an incident." \
                 "\ncontextPath: VeryBigWord.Endpoint.vm.orchestration_details.orchestration_obj_id" \
                 "\ndescriptionMessage: The orchestration object identifier for an Endpoint's virtual machine." \
                 "\ncontextPath: AAA.Endpoint.status\ndescriptionMessage: The status of an Endpoint (off/on)." \
                 "\ncontextPath: DDDdddRRR.Endpoint.is_on_alert\ndescriptionMessage: Whether the endpoint is on or not." \
                 "\ncontextPath: Blabla.Endpoint.active\ndescriptionMessage: Whether the endpoint is on or off." \
                 "\ncontextPath: Guardicore.Endpoint.nics.is_cloud_public\ndescriptionMessage: Whether the Endpoint's NIC is in the public cloud or not." \
                 "\ncontextPath: Activity.Endpoint.active\ndescriptionMessage: Whether the Endpoint is on or off." \
                 "\ncontextPath: IDID.Endpoint.host_orchestration_id\ndescriptionMessage: The orchestration object identifier for the Endpoint's host." \
                 "\ncontextPath: BrublaBRO.Endpoint.is_on\ndescriptionMessage:  Whether the Endpoint is on or not." \
                 "\ncontextPath: WellDone.Endpoint.metadata.InventoryAPI.report_source\ndescriptionMessage:  The Endpoint's InvestoryAPI report source." \
                 "\ncontextPath: SomethingElse.Endpoint.bios_uuid\ndescriptionMessage:"
LOADING_DONE = False
INPUT_PREFIX = '\r>> Generated output: '
DEBUG_PROMPT = False


def pinput(prompt, prefill=''):
    import readline
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()


def clear_prompt():
    global CURRENT_PROMPT
    if len(CURRENT_PROMPT) >= 2000 * 4:
        y = input("Can't teach model anymore (prompt too big), clear?")
        if y == 'y':
            print("Truncating prompt:")
            print(CURRENT_PROMPT)
            CURRENT_PROMPT = ""
            print('Teaching from blank now')


def correct_prompt(ctx, correct_desc):
    global CURRENT_PROMPT
    clear_prompt()
    CURRENT_PROMPT += f"contextPath: {ctx}\ndescriptionMessage: {correct_desc}\n"


def get_current_prompt():
    global CURRENT_PROMPT
    return CURRENT_PROMPT


def animate():
    ''' Show a nice animation spinner '''
    global LOADING_DONE
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if LOADING_DONE:
            break
        print(INPUT_PREFIX + c, end="", flush=True)
        time.sleep(0.1)


def generate_desc_with_spinner(command_ctx, insecure, output, verbose):
    global LOADING_DONE
    LOADING_DONE = False
    t = threading.Thread(target=animate)
    t.start()
    output = generate_desc(command_ctx, verbose=verbose,
                           prob_check=True,
                           insecure=insecure)
    LOADING_DONE = True
    return output


def generate_desc(input_ctx, verbose=False,
                  prob_check=False, insecure=False):
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    prompt = get_current_prompt()
    prompt += f"contextPath: {input_ctx}\ndescriptionMessage:"

    if verbose:
        logger.debug("=" * 25)
        logger.debug("PROMPT: ")
        logger.debug(prompt)
        logger.debug("=" * 25)
        logger.debug("Using GPT-3...")

    if insecure:
        return ai21_api_request(prompt, {"prob_check": prob_check,
                                         "insecure": insecure})
    return ai21_api_request(prompt, {"prob_check": prob_check})


def ai21_api_request(prompt, options={}):
    res = requests.post(
        "https://api.ai21.com/studio/v1/j1-large/complete",
        headers={"Authorization": f"Bearer {os.environ.get('AI21_KEY')}"},
        json={
            "prompt": prompt,
            "numResults": 1,
            "maxTokens": 8,
            "stopSequences": STOP_SEQS,
            "topKReturn": 0,
            "temperature": 0.0
        },
        verify=options.get("insecure", False)
    )

    data = res.json().get("completions")[0].get("data")
    output = data.get("text")
    prob_check = options.get("prob_check", False)

    if prob_check:
        output = build_description_with_probabilities(data)
    return output.strip()


def build_description_with_probabilities(data):
    """ Build the description and wrap low probabilities with *'s """
    output = ""
    PROBABILITY_THREASHOLD = 0.2  # less than 20% sure, higher is more precise.
    tokens = data.get("tokens")
    for token in tokens:
        token = token.get("generatedToken")
        i = token.get("token").replace("▁", " ").replace("<|newline|>", "")
        v = token.get("logprob")
        if i in STOP_SEQS:
            break
        v = math.exp(v)

        # Wrap low probability tokens with **'s
        if v < PROBABILITY_THREASHOLD:
            output += f" **{i.lstrip()}**"
        else:
            output += i
    return output


def write_desc(c_index, final_output, o_index, output_path, verbose, yml_data):
    if verbose:
        logger.debug(f"Writing: {final_output}\n---")
    yml_data['script']['commands'][c_index]['outputs'][o_index][
        'description'] = final_output
    write_yml(output_path, yml_data)


def correct_interactively(command_ctx, final_output, output):
    print('\r', end='', flush=True)
    final_output = pinput('>> Generated output: ',
                          final_output)
    # Learn from mistakes
    if final_output != output:
        y = input("Should we append to prompt (y/n)? ")
        if y == 'y':
            print(
                f"(Correcting prompt `{final_output}` instead of `{output}`)")
            correct_prompt(command_ctx, final_output)
    return final_output


def print_experimental():
    print()
    print("⚠" * 100)
    print('''███████ ██   ██ ██████  ███████ ██████  ██ ███    ███ ███████ ███    ██ ████████  █████  ██
    ██       ██ ██  ██   ██ ██      ██   ██ ██ ████  ████ ██      ████   ██    ██    ██   ██ ██
    █████     ███   ██████  █████   ██████  ██ ██ ████ ██ █████   ██ ██  ██    ██    ███████ ██
    ██       ██ ██  ██      ██      ██   ██ ██ ██  ██  ██ ██      ██  ██ ██    ██    ██   ██ ██
    ███████ ██   ██ ██      ███████ ██   ██ ██ ██      ██ ███████ ██   ████    ██    ██   ██ ███████
    ''')
    print("this feature is experimental, use with caution.")
    print("⚠" * 100)
    print()


def generate_ai_descriptions(
        input_path: str,
        output_path: str = "out.yml",
        interactive: bool = True,
        verbose: bool = False,
        insecure: bool = False,
):
    """ Generate integration command contexts.

    Args:
        input_path: path to the yaml integration input path
        output_path: path to the yaml integration output path
        interactive: interactivity (correct ai result mistakes)
        verbose: verbose (debug mode)
        insecure: insecure https (debug mode)
    """
    print_experimental()

    if verbose:
        logger.setLevel(logging.DEBUG)

    try:
        similar_paths: Dict[str, str] = {}
        yml_data = get_yaml(input_path)

        # Fix sometimes the yml doesn't contain the full structure
        #  (json-to-outputs)
        if 'script' not in yml_data:
            yml_data = {'script': {'commands': [yml_data]}}

        commands = yml_data.get("script", {})
        commands = commands.get('commands', [])

        # Iterate over every command
        for c_index, command in enumerate(commands):
            command_name = command.get('name')

            if interactive or verbose:
                logger.debug(f'Command: {command_name}')

            outputs = command.get('outputs')
            if not outputs:
                if interactive or verbose:
                    logger.debug("-- Skipping because no outputs for command")
                continue

            # Iterate over every output per command
            for o_index, o in enumerate(outputs):
                command_ctx = o.get('contextPath')

                # Match past paths automatically.
                if command_ctx in similar_paths:
                    print(
                        f"--Already added description for exact path: {command_ctx}--")
                    final_output = similar_paths.get(command_ctx)
                    yml_data['script']['commands'][c_index]['outputs'][o_index][
                        'description'] = final_output
                    write_yml(output_path, yml_data)
                    continue

                # Print the progress and current context path
                if interactive or verbose:
                    print(f'\n{o_index + 1}/{len(outputs)}')
                    print(f'Context: {command_ctx}')

                output = "No result from GPT."

                # Generate a description with AI21 API (retry twice in case we
                # have a long prompt we need to clear).
                for _exception in range(2):
                    try:
                        output = generate_desc_with_spinner(command_ctx,
                                                            insecure, output,
                                                            verbose)
                        break
                    except requests.exceptions.RequestException as e:
                        print('Failed AI description request: ', e)
                        clear_prompt()
                        continue

                final_output = output

                # Correct the description if needed interactively
                if interactive:
                    final_output = correct_interactively(command_ctx,
                                                         final_output, output)

                # Write the final description to the file (backup)
                write_desc(c_index, final_output, o_index, output_path, verbose,
                           yml_data)

                # Update the similar context paths
                similar_paths[command_ctx] = str(final_output)

            # Backup the prompt for later usage (in case we cleared the prompt)
            if DEBUG_PROMPT:
                with open(f"backup_prompt_ai_{c_index}.txt", "w") as ai_prompt_file:
                    ai_prompt_file.write(get_current_prompt())
    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return
