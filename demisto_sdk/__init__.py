import os

if not os.environ.get("DEMISTO_SDK_SKIP_LOGGER_SETUP", False):
    from demisto_sdk.commands.common.logger import logging_setup

    logging_setup(initial=True, calling_function="__init__")
