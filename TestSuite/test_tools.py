import os
from typing import List, Tuple

from demisto_sdk.commands.common.logger import logger


def get_test_suite_path():
    """Gets root of Demisto-SDK Test Suite folder (For assets management)
    Returns root of TestSuite
    """
    return os.path.dirname(os.path.abspath(__file__))


def suite_join_path(*args: str):
    """Gets root of Demisto-SDK TestSuite folder (For assets management) joined by suffix

    Args:
        args: paths to join

    Returns:
        Joined path
    """
    return os.path.join(get_test_suite_path(), *args)


class ChangeCWD:
    """
    Temporary changes the cwd to the given dir and then reverts it.
    Use with 'with' statement.
    """

    def __init__(self, directory):
        self.current = os.getcwd()
        self.directory = directory

    def __enter__(self):
        os.chdir(self.directory)

    def __exit__(self, *args):
        os.chdir(self.current)


def str_in_call_args_list(
    call_args_list: List[Tuple[Tuple[str], Tuple[str], Tuple[str]]], required_str: str
):
    """
    Checks whether required_str is in any of the call_args in call_args_list
    Args:
        call_args_list: From a mocker
        required_str: String to search in any of the call_args_list
    :return: True is required_str was found, False otherwise
    """
    ret_value = any(
        isinstance(current_call[0], tuple) and required_str in current_call[0][0]
        for current_call in filter(None, call_args_list)
    )
    if not ret_value:
        logger.info(f"Could not find {required_str=}")
    return ret_value


def count_str_in_call_args_list(
    call_args_list: List[Tuple[Tuple[str], Tuple[str], Tuple[str]]], search_str: str
):
    """
    Countes the number of times search_str appears in any of the call_args in call_args_list.
    Several appearances in a single call_args_list counts as 1.
    Args:
        call_args_list: From a mocker
        search_str: String to search in any of the call_args_list
    :return: The number of times search_str appears in any of the call_args in call_args_list
    """
    return sum(
        1
        for call in filter(None, call_args_list)
        if call[0]
        and isinstance(call[0], tuple)
        and call[0][0]
        and search_str in call[0][0]
    )
