if __name__ == "__main__":
    from demisto_sdk.commands.common.logger import logging_setup

    logging_setup(initial=True, calling_function="__init__")
