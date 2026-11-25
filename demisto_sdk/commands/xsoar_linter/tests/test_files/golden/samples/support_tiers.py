"""Sample: one violation of every rule, used to check which rules run at each support level."""

import sys
import time

from CommonServerPython import tableToMarkdown

URL = "http://example.com"
PARAMS = demisto.params()


def helper(value):
    print(value)
    time.sleep(20)
    exit()
    quit()
    sys.exit(1)
    demisto.log("x")
    demisto.results("x")
    return_outputs("x")
    return_error("first")
    return_error("second")
    return CommandResults(indicators=[])


def main() -> None:
    args = demisto.args()
    value = args["key"]
    helper(value)
