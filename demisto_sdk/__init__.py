import os

if os.environ.get("DEMISTO_SDK_SKIP_LOGGER_SETUP", "False").lower() not in [
    "true",
    "yes",
    "1",
]:
    from demisto_sdk.commands.common.logger import logging_setup

    logging_setup(initial=True, calling_function="__init__")
