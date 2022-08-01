import warnings

import urllib3


def pytest_sessionstart(session):
    # disable warnings
    urllib3.disable_warnings()


def pytest_sessionfinish(session):
    # return warnings to default
    warnings.simplefilter("default", urllib3.exceptions.HTTPWarning)
