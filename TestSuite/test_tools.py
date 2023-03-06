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
        if current_call and isinstance (current_call[0], tuple):
            if required_str in current_call[0][0]:
                return True
    return False


def assert_str_in_call_args_list(call_args_list, required_str):
    """
    Checks whether required_str is in any of the call_args in call_args_list
    Args:
        call_args_list: From a mocker
        required_str: String to search in any of the call_args_list
    :return: True is required_str was found, False otherwise
    """
    ret_value = False
    for current_call in call_args_list:
        if type(current_call[0]) == tuple:
            if required_str in current_call[0][0]:
                ret_value = True
    assert ret_value


def assert_strs_in_call_args_list(call_args_list, required_strs):
    """
    Checks whether required_str is in any of the call_args in call_args_list
    Args:
        call_args_list: From a mocker
        required_str: String to search in any of the call_args_list
    :return: True is required_str was found, False otherwise
    """
    for current_required_str in required_strs:
        assert_str_in_call_args_list(call_args_list, current_required_str)
