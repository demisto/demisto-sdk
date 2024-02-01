import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_approved_tags_from_branch,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Parameter
from demisto_sdk.commands.content_graph.objects.playbook import Playbook


def collect_all_inputs_in_use(content_item: Playbook) -> Set[str]:
    """
    Args:
        - content_item (Playbook): The content item to collect inputs from.
    Returns:
        - Set of all inputs used in playbook.
    """
    result: Set = set()
    playbook_text = content_item.text
    all_inputs_occurrences = re.findall(r"inputs\.[-\w ?!():]+", playbook_text)
    for input in all_inputs_occurrences:
        input = input.strip()
        splitted = input.split(".")
        if len(splitted) > 1 and splitted[1] and not splitted[1].startswith(" "):
            result.add(splitted[1])
    return result


def collect_all_inputs_from_inputs_section(content_item: Playbook) -> Set[str]:
    """
    Args:
        - content_item (Playbook): The content item to collect inputs from.
    Returns:
        - A set of all inputs defined in the 'inputs' section of playbook.
    """
    inputs: dict = content_item.data.get("inputs", {})
    inputs_keys = [input["key"].strip() for input in inputs if input["key"]]
    return set(inputs_keys)


def filter_by_marketplace(
    marketplaces: List, pack_meta_file_content: Dict, return_is_valid=True
):
    """Filtering pack_metadata tags by marketplace"""

    pack_tags: Dict[str, List[str]] = {}
    for marketplace in marketplaces:
        pack_tags[marketplace] = []
    pack_tags["common"] = []

    is_valid = True
    for tag in pack_meta_file_content.get("tags", []):
        if ":" in tag:
            tag_data = tag.split(":")
            tag_marketplaces = tag_data[0].split(",")

            try:
                for tag_marketplace in tag_marketplaces:
                    pack_tags[tag_marketplace].append(tag_data[1])
            except KeyError:
                logger.warning(
                    "[yellow]You have non-approved tag prefix in the pack metadata tags, cannot validate all tags until it is fixed."
                    f' Valid tag prefixes are: { ", ".join(marketplaces)}.[/yellow]'
                )
                is_valid = False

        else:
            pack_tags["common"].append(tag)
    if return_is_valid:
        return pack_tags, is_valid
    else:
        return pack_tags


def extract_non_approved_tags(
    pack_tags: Dict[str, List[str]], marketplaces: List
) -> Set[str]:
    approved_tags = get_approved_tags_from_branch()

    non_approved_tags = set(pack_tags.get("common", [])) - set(
        approved_tags.get("common", [])
    )
    for marketplace in marketplaces:
        non_approved_tags |= set(pack_tags.get(marketplace, [])) - set(
            approved_tags.get(marketplace, [])
        )

    return non_approved_tags


def validate_categories_approved(categories: list, approved_list: list):
    """
    Check that the pack categories contain only approved categories.

    Args:
        categories (list): the list of the pack's categories.
        approved_list (list): the predefined approved categories list.

    Returns:
        bool: True if all the pack categories is from the approved list. Otherwise, return False.
    """
    for category in categories:
        if category not in approved_list:
            return False
    return True


def get_default_output_description():
    return json.loads(
        (
            Path(__file__).absolute().parents[1]
            / "common/default_output_descriptions.json"
        ).read_text()
    )


def find_param(params: List[Parameter], param_to_find: str) -> Optional[Parameter]:
    """Retrieve the parameter with the given name.

    Args:
        params (List[Parameter]): The integration's params list.
        param_to_find (str): The name of the param we wish to find.

    Returns:
        Command: The Parameter with the given name or None.
    """
    for param in params:
        if param.name == param_to_find:
            return param
    return None


def find_command(commands: List[Command], command_to_find: str) -> Optional[Command]:
    """Retrieve the command with the given name.

    Args:
        commands (List[Command]): The integration's commands list.
        command_to_find (str): The name of the command we wish to find.

    Returns:
        Command: The command with the given name or None.
    """
    for command in commands:
        if command.name == command_to_find:
            return command
    return None
