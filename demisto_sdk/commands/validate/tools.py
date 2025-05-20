import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set

from packaging.version import parse

from demisto_sdk.commands.common.constants import (
    CONTENT_ITEM_SECTION_REGEX,
    CONTENT_TYPE_SECTION_REGEX,
    GitStatuses,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    filter_out_falsy_values,
    get_approved_tags_from_branch,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import (
    Command,
    Integration,
    Parameter,
)
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.objects.test_script import TestScript


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
                    "<yellow>You have non-approved tag prefix in the pack metadata tags, cannot validate all tags until it is fixed."
                    f' Valid tag prefixes are: { ", ".join(marketplaces)}.</yellow>'
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


def compare_lists(sub_list: List[str], main_list: List[str]) -> List[str]:
    """
    Compares two lists and returns the elements that are in the sub list but not in the main list, including duplicates.
    for example:
    compare_lists(['a', 'b', 'c', 'c', 'd'], ['a', 'b', 'c']) -> ['c', 'd']
    Args:
        sub_list: list of elements to compare if they are a subset of main_list
        main_list: the list to compare against
    Returns:
        List the elements that appear in the sublist but not in the main list, including duplicates if they are not all present in the main list.
    """
    return list((Counter(sub_list) - Counter(main_list)).elements())


def is_indicator_pb(playbook: Playbook):
    """
    Check if the playbook has indicators as input query.
    """
    return any(
        (i.get("playbookInputQuery") or {}).get("queryEntity") == "indicators"
        for i in playbook.data.get("inputs", {})
    )


def extract_rn_headers(
    rn_content: str,
    remove_prefixes: bool = False,
) -> Dict[str, List[str]]:
    """
        Extracts the headers from the release notes file.
    Args:
        rn_content (str): The release notes file content.
        remove_prefixes (bool, default: False): If true, removes prefixes from headers and keeps only the display names.
    Return:
        A dictionary representation of the release notes file that maps content types' headers to their corresponding content items' headers.
        i.e: {"Integrations": ["integration_1", "integration_2"], "Scripts: ["script_1]}
    """
    headers: Dict = {}
    header_index = 0
    content_index = 1
    # Get all sections from the release notes using regex
    rn_sections = CONTENT_TYPE_SECTION_REGEX.findall(rn_content)
    for section in rn_sections:
        section = filter_out_falsy_values(ls=section)
        content_type = section[header_index]
        content_type_sections_str = section[content_index]
        content_type_sections_ls = CONTENT_ITEM_SECTION_REGEX.findall(
            content_type_sections_str
        )
        if not content_type_sections_ls:
            #  Did not find content items headers under content type - might be due to invalid format.
            #  Will raise error in rn_valid_header_format.
            headers[content_type] = []
        for content_type_section in content_type_sections_ls:
            content_type_section = filter_out_falsy_values(ls=content_type_section)
            if content_type_section:
                header = content_type_section[header_index]
                if headers.get(content_type):
                    headers[content_type].append(header)
                else:
                    headers[content_type] = [header]
    if remove_prefixes:
        filter_rn_headers_prefix(headers)
    return headers


def filter_rn_headers_prefix(headers: Dict) -> None:
    """
        Filters out the headers from the release notes file, removing add-ons such as "New" and "**".
    Args:
        headers: (Dict) - The release notes headers to filter, the structure is content type -> headers.(e.g. Integrations -> [header1, header2])
    Return:
        None.
    """
    for content_type, content_items in headers.items():
        content_items = filter_out_falsy_values(ls=content_items)
        headers[content_type] = [
            item.replace("New:", "").strip() for item in content_items
        ]


def was_rn_added(p: Pack) -> bool:
    return p.release_note.git_status == GitStatuses.ADDED


def is_new_pack(p: Pack) -> bool:
    return p.git_status == GitStatuses.ADDED and p.pack_version == parse("1.0.0")


def is_pack_move(content_item: ContentItem) -> bool:
    old_content = content_item.old_base_content_object
    assert isinstance(old_content, ContentItem)
    return content_item.pack_id != old_content.pack_id


def should_skip_rn_check(content_item: ContentItem) -> bool:
    """Determines whether a RN validation should run on the given content item.
    Assumptions:
    - Only modified content items should have RNs
      - Integration is considered modified if its description file was modified
      - A modeling rule is considered modified if its XIF and schema files are modified
      - A movement between packs is considered a modification
    - Test content items shouldn't have RNs
    - Silent content items shouldn't have RNs

    Args:
        content_item (ContentItem): A content item object

    Returns:
        bool: True iff should run the RN validaion.
    """
    if isinstance(content_item, (TestPlaybook, TestScript)):
        return True
    if content_item.is_silent:
        return True
    if isinstance(content_item, Integration):
        return (
            not content_item.git_status and not content_item.description_file.git_status
        )
    if isinstance(content_item, ModelingRule):
        return (
            not content_item.git_status
            and not content_item.xif_file.git_status
            and not content_item.schema_file.git_status
        )
    if content_item.git_status == GitStatuses.RENAMED:
        return not is_pack_move(content_item)
    return content_item.git_status is None
