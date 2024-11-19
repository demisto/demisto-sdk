if __name__ in ["__main__", "demisto_sdk"]:
    from demisto_sdk.commands.common.logger import logging_setup

    logging_setup(initial=True, calling_function="__init__")
