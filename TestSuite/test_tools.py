import os


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


def str_in_call_args_list(call_args_list, required_str):
    """
    Checks whether required_str is in any of the call_args in call_args_list
    Args:
        call_args_list: From a mocker
        required_str: String to search in any of the call_args_list
    :return: True is required_str was found, False otherwise
    """
    for current_call in call_args_list:
        if current_call and isinstance(current_call[0], tuple):
            if required_str in current_call[0][0]:
                return True
    print(f"Could not find {required_str=}")
    return False


def count_str_in_call_args_list(call_args_list, search_str):
    """
    Countes the number of times search_str appears in any of the call_args in call_args_list.
    Several appearances in a single call_args_list counts as 1.
    Args:
        call_args_list: From a mocker
        search_str: String to search in any of the call_args_list
    :return: The number of times search_str appears in any of the call_args in call_args_list
    """
    return sum(1 for call in filter(None, call_args_list) if call[0] and isinstance(call[0], tuple) and call[0][0] and search_str in call[0][0])
