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
