## autogenerate-yaml-from-python

**Use Case**

This command uses Python annotations (supported in 3.5+, though many commonly used annotations are only since
3.9) to autogenerate integration YAML from a provided python integration script.

This process can save a large amount of time for larger, complex integrations as it removes the need to write
any YAML.

For this command to work, the underlying code must comply with some boilerplate and formatting, which is
described in detail below.

**CommandRegister**

The CommandRegister class, instantiated as global variable `COMMANDS`, stores all the XSOAR commands the
integration provides. An example implementation is below;

```python
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

    def run_command_result_command(self, command_name: str, func: Callable,
                                   demisto_args: dict) -> CommandResults:
        """
        Runs the normal XSOAR command and converts the returned dataclas instance into a CommandResults
        object.
        """
        result = func(**demisto_args)
        if command_name == "test-module":
            return_results(result)

        if not result:
            command_result = CommandResults(
                readable_output="No results.",
            )
            return_results(command_result)
            return command_result

        if type(result) is list:
            outputs = [vars(x) for x in result]
            summary_list = [vars(x) for x in result]
            title = result[0]._title
            output_prefix = result[0]._output_prefix
        else:
            outputs = vars(result)
            summary_list = [vars(result)]
            title = result._title
            output_prefix = result._output_prefix

        extra_args = {}
        if hasattr(result, "_outputs_key_field"):
            extra_args["outputs_key_field"] = getattr(result, "_outputs_key_field")

        readable_output = tableToMarkdown(title, summary_list)
        command_result = CommandResults(
            outputs_prefix=output_prefix,
            outputs=outputs,
            readable_output=readable_output,
            **extra_args
        )
        return_results(command_result)
        return command_result

    def run_file_command(self, func: Callable,
                         demisto_args: dict) -> dict:

        file_result: dict = func(**demisto_args)
        return_results(file_result)
        return file_result

    def is_command(self, command_name: str) -> bool:
        if command_name in self.commands or command_name in self.file_commands:
            return True

        return False

    def run_command(
            self,
            command_name: str,
            demisto_args: dict
    ) -> Union[CommandResults, dict]:
        """
        Runs the given XSOAR command.
        :param command_name: The name of the decorated XSOAR command.
        :param demisto_args: Result of demisto.args()
        """
        if command_name in self.commands:
            func = self.commands.get(command_name)
            return self.run_command_result_command(command_name, func, demisto_args)  # type: ignore

        if command_name in self.file_commands:
            func = self.file_commands.get(command_name)
            return self.run_file_command(func, demisto_args)  # type: ignore

        raise DemistoException("Command not found.")


# This is the store of all the commands available to this integration
COMMANDS = CommandRegister()
```

The above snippet;

* provides a store of commands (commands and file_commands)
* decorates "outer" XSOAR functions
* Converts the return value of those functions to the demisto class `CommandResults`.

CommandRegister can be changed to pass common arguments such as an API handler automatically to commands or to
perform output validation after each command.

**Dataclasses**

Dataclasses are used to describe command outputs, where each attribute represents an output key. In simple
calls, API data can be passed directly into a dataclass object as **kwargs.

Dataclasses declare the output prefix and the human readable title. The above CommandRegister implementation
automatically formats the dataclass result object as a table.

You can document each output key using `:param <key>: <description>` in the docstring.

```python
@dataclass
class ExampleReturnClass:
    """
    :param example_attr: An Example output attribute
    """
    example_attr: str
    _output_prefix = "Example"
    _title = "This is some example data"
```

**Functions**

Functions that represent commands are decorated by CommandRegister.command(). They must provide annotations
for at least the output, and the decorator argument denotes the command name. The docstring in the function
becomes the command description, including descriptions for each arguments via `:param`

```python
@COMMANDS.command("fake-command")
def fake_command(fake_argument: str) -> ExampleReturnClass:
    """
    This is an example command with a simple, mandatory string argument.
    :param fake_argument: This is a fake argument
    """
    return ExampleReturnClass(
        example_attr="Hi, this is an example returned object."
    )
```

Command functions can also specify that they return a list using `list[<dataclass type>]`.

Function arguments are important, as they represent command arguments in XSOAR. Here, the type and default
values are both used.

Function arguments without any default become *required* command arguments;

```python
def fake_command(fake_argument: str) -> ExampleReturnClass:
```

Function arguments with a default are *optional* command arguments, with the default value honored;

```python
def fake_command(fake_argument: str = "Default Value") -> ExampleReturnClass:
```

Function arguments that are type `list` have *is array* enabled within XSOAR;

```python
def fake_command(fake_argument: list) -> ExampleReturnClass:
```

Finally, for command arguments that have a predefined list, you use an enum type argument. In the below
example, the two predefined values will be `FirstOption,SecondOption`

```python
class ExampleEnum(enum.Enum):
    EXAMPLE_FIRST_OPTION = "FirstOption"
    EXAMPLE_SECOND_OPTION = "SecondOption"


@COMMANDS.command("fake-command-enum-argument")
def fake_command_optional_argument(fake_enum_argument: ExampleEnum):
```

**DemistoParameters**

This class defines the parameters/config for the integration. You only need to have this class created, you
don't need to consume it in order for the autogeneration to work.

```python
@dataclass
class DemistoParameters:
    """
    Demisto Parameters
    :param  example_integration_param: Example Param
    """
    example_integration_param: str
    credentials: dict
```

**Merging Integration YAML**

This command can merge autogenerated commands with an existing YAML integration. You may want to do this if
you have to ever customize any components of the YAML beyond what autogeneration provides, but you still want
to generate the majority of the YAML config.

If `--merge` is provided, the YAML will be generated as normal, but only the commands will be copied into an
existing configuration file.

**Options**
---
*  **-f, --integration_path PATH**
    Path to python integration.
*  **-n, --integration_name**
    Name of integration - must match python script name as it's used in import
*  **--output**
    Location to write autogenerated integration YAML to
*  **--merge/--no-merge**
    Whether to merge the autogenerated commands with an existing YAML integration file
*  **-c, --category**
    Integration Category
*  **-d, --description**
    Integration Description
*  **--docker_image**
    Docker image in use - will override existing value if merging
*  **--runonce**
    Enable runonce flag in integration
*  **--feed**
    Enable feed flag in integration 
*  **--fetch**
    Enable fetch flag in integration 

**Examples**:
---
`demisto-sdk autogenerate-from-python -f Packs/PAN-OS/Integrations/Panorama/Panorama.py -n "Panorama" --output Packs/PAN-OS/Integrations/Panorama/Panorama.yml`
Details:

1. Autogenerate will run on `Packs/PAN-OS/Integrations/Panorama/Panorama.py`
2. YAML integration will be saved to `Packs/PAN-OS/Integrations/Panorama/Panorama.yml`

`demisto-sdk autogenerate-from-python --merge -f Packs/PAN-OS/Integrations/Panorama/Panorama.py -n "Panorama" --output Packs/PAN-OS/Integrations/Panorama/Panorama.yml`
Details:

1. Autogenerate will run on `Packs/PAN-OS/Integrations/Panorama/Panorama.py`
2. YAML integration will be merged with `Packs/PAN-OS/Integrations/Panorama/Panorama.yml`