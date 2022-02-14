"""This file is a part of the generating yml design. Generating a yml file from a python file."""


class DetailsCollector:
    """The DetailsCollector class provides decorators for integration
    functions which contain details relevant to yml generation.

    If collect_data is set to true, calling the decorated functions will result in
    collecting the relevant details and not running them. If it is set to false,
    the run should remain unchanged.
    """

    def __init__(self, conf):
        self.docs = {}
        self.commands = []
        self.collect_data = False
        self.conf = conf

    def set_collect_data(self, value):
        """A setter for collect_data."""
        self.collect_data = value

    def add_command(self, command_name=None):
        """A decorator example. Its' arguments are extra inputs specified in the call.
        It returns a wrapper which collects details of a command functions
        if collect_data is set to True.
        """
        print("adding command")

        def add_command_wrapper(func):
            """The wrapper of the command function."""
            def get_out_info(*args, **kwargs):
                """The function which will collect data if needed or
                run the original function instead."""
                print(f"collect_data {self.collect_data}")
                # Here it is
                if self.collect_data:
                    print("collecting")
                    self.docs[command_name] = func.__doc__
                else:
                    func(*args, **kwargs)
            return get_out_info

        # More information collection can be done here
        self.commands.append(command_name)
        return add_command_wrapper
