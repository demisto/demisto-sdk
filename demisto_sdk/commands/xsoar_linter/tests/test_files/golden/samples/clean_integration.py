"""Sample: a clean integration that follows all conventions."""

import demistomock as demisto
from CommonServerPython import *


def test_module(client: dict) -> str:
    return "ok"


def get_item_command(client: dict, args: dict) -> CommandResults:
    item_id = args.get("item_id")
    return CommandResults(outputs_prefix="Vendor.Item", outputs={"id": item_id})


def main() -> None:
    params = demisto.params()
    args = demisto.args()
    command = demisto.command()
    demisto.debug(f"Command being called is {command}")
    try:
        client = {"url": params.get("url")}
        if command == "test-module":
            return_results(test_module(client))
        elif command == "vendor-get-item":
            return_results(get_item_command(client, args))
        else:
            raise NotImplementedError(f"Command {command} is not implemented")
    except Exception as e:
        return_error(f"Failed to execute {command} command.\nError:\n{str(e)}")


if __name__ in ("__main__", "__builtin__", "builtins"):
    main()
