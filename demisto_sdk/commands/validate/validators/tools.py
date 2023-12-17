from typing import Set
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
import re
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