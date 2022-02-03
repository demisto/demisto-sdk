from typing import Callable
from dataclasses import dataclass


class CommandRegister:
    commands: dict[str, Callable] = {}
    file_commands: dict[str, Callable] = {}

    def command(self, command_name: str):
        """
        Register a normal Command for this Integration. Commands always return CommandResults.

        :param command_name: The XSOAR integration command
        """

        def _decorator(func):
            self.commands[command_name] = func

            def _wrapper(topology, demisto_args=None):
                return func(topology, demisto_args)

            return _wrapper

        return _decorator

    def file_command(self, command_name: str):
        """
        Register a file command. file commands always return FileResults.

        :param command_name: The XSOAR integration command
        """

        def _decorator(func):
            self.file_commands[command_name] = func

            def _wrapper(topology, demisto_args=None):
                return func(topology, demisto_args)

            return _wrapper

        return _decorator


# This is the store of all the commands available to this integration
COMMANDS = CommandRegister()


@dataclass
class ExampleReturnClass:
    """
    :param example_attr: An Example output attribute
    """
    example_attr: str
    _output_prefix = "Example"
    _title = "This is some example data"


@COMMANDS.command("fake-command")
def fake_command(fake_argument: str) -> ExampleReturnClass:
    """
    This is an example command.
    :param fake_argument: This is a fake argument
    """
    pass


@COMMANDS.command("fake-command-optional-argument")
def fake_command_optional_argument(fake_optional_argument: str = ""):
    """
    This is an example command.
    :param fake_optional_argument: This is a fake argument
    """
    pass