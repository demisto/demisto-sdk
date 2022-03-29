# Generate YML from python
Generate YML file from python code that includes special syntax.
The output file name will be the same as the python code with the .yml ending instead of .py.

**Arguments**
* **-i, --input**
   (Required) The path to the python code to generate from.
* **-v, --verbose**
   Flag for extended prints.
* **-f, --force**
   Override existing yml file. If not used and yml file already exists, the script will not generate a new yml file.


## Features and Usage
### Importing
If the following line:
```python
from CommonServerPython import *
```
is in your code, **no importing is required**.

Otherwise if you are making a standalone integration:

If you have demisto-sdk as a dependency in your project, you can use the following import:
```python
from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (CommandMetadata, ConfKey, InputArgument, YMLMetadataCollector,OutputArgument, ParameterTypes)
```
If you don't have demisto-sdk installed as a dependency and do not wish to, you can add the following implementation to your code, or add it as a separate file and import it:
```python
from unittest.mock import MagicMock
from typing import Optional, Any, Union, Callable

# Mocks for YML generation
InputArgument = MagicMock()
OutputArgument = MagicMock()
ConfKey = MagicMock()

class YMLMetadataCollector:
    def __init__(self, integration_name: str, docker_image: str = "demisto/python3:latest",
                 description: Optional[str] = None, category: str = "Utilities", conf: Optional[List[ConfKey]] = None,
                 is_feed: bool = False, is_fetch: bool = False, is_runonce: bool = False,
                 detailed_description: Optional[str] = None, image: Optional[str] = None, display: Optional[str] = None,
                 tests: list = ["No tests"], fromversion: str = "6.0.0",
                 long_running: bool = False, long_running_port: bool = False, integration_type: str = "python",
                 integration_subtype: str = "python3", deprecated: Optional[bool] = None, system: Optional[bool] = None,
                 timeout: Optional[str] = None, default_classifier: Optional[str] = None,
                 default_mapper_in: Optional[str] = None,
                 integration_name_x2: Optional[str] = None, default_enabled_x2: Optional[bool] = None,
                 default_enabled: Optional[bool] = None, verbose: bool = False):
        pass

    def command(self, command_name: str, outputs_prefix: Optional[str] = None,
                outputs_list: Optional[list] = None, inputs_list: Optional[list] = None,
                execution: Optional[bool] = None, file_output: bool = False,
                multiple_output_prefixes: bool = False, deprecated: bool = False, restore: bool = False,
                description: Optional[str] = None) -> Callable:
        def command_wrapper(func):
            def get_out_info(*args, **kwargs):
                if restore:
                    kwargs['command_name'] = command_name
                    kwargs['outputs_prefix'] = outputs_prefix
                    kwargs['execution'] = execution
                return func(*args, **kwargs)

            return get_out_info

        return command_wrapper
```
This will ensure your code runs even though it uses the undefined YMLMetadataCollector objects.

### Initialization and Integration Configuration
The initialization begins with the YMLMetadataCollector object in the following way:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")
```
* It is very important that the **name of the initialized object is `metadata_collector`**. Otherwise the generation will not work.
* The only mandatory argument for the YMLMetadataCollector is the integration_name which will be used as your integration id.
* All other arguments concerning the whole integration will be passed in this initialization as well. See the initialization examples in the sections below.
Other arguments include:
```python
integration_name, display, image, detailed_description,
description, category, tests, fromversion, system,
timeout, default_classifier, default_mapper_in, default_enabled,
deprecated, default_enabled_x2, integration_name_x2
docker_image, is_feed, is_fetch, is_runonce, long_running,
long_running, long_running_port, type, subtype
```

#### ConfKey
To specify integration configuration keys use the keyword `conf=[ConfKey(), ConfKey()]` like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name",
                                                      conf=[ConfKey(name="some_name",
                                                                    key_type=ParameterTypes.STRING),
                                                            ConfKey(name="some_other_name",
                                                                    key_type=ParameterTypes.NUMBER)])
```
ConfKey arguments include:
```python
name, display, default_value, required, additional_info, options, input_type
```

Where `key_type` takes argument of type `ParameterTypes` which is exactly the same as `ParameterType` that can be found in
`demisto_sdk.commands.common.constants`

The trailing `s` was added to reduce circular imports.

The argument `options` takes a list of strings and specifies the argument as predefined and the list as the options.

And `input_type` takes and enum class and results in the enum attributes as the predefined options.
Usage example:
```python
class InputOptions(enum.Enum):
    A = "a"
    B = "b"

metadata_collector = YMLMetadataCollector(integration_name="some_name",
                                           conf=[ConfKey(name="some_name",
                                                         input_type=InputOptions)])
```
will result in the following metadata for the configuration key:
```json
{
    "display": "some_name",
    "name": "some_name",
    "type": 0,
    "required": false,
    "options": ["a", "b"]
}
```

### Adding Commands
#### General
To add command metadata, you have to wrap the command function using `@metadata_collector.command()`
like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky_command")
def funky_command():
    print("funk")
```
The only mandatory argument is `command_name`. Other `metadata_collector.command` arguments inculde
```python
deprecated, execution, description, outputs_prefix, outputs_list,
inputs_list, file_output, multiple_output_prefixes
```
##### Restored Args
In order to reduce code duplication, you can reuse the following arguments:
```python
command_name, outputs_prefix, execution
```
In the following way:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command", outputs_prefix="funk", execution=False, restore=True)
def funky_command(client, command_name, outputs_prefix, execution):
    """Some funky command"""
    print(f"The command name is {command_name} output_prefix is {outputs_prefix} and execution {execution}")
```
When running `funky_command(client=SomeClient)` the following will be printed:
```
The command name is funky-command output_prefix is funk and execution False
```
Warnings:
* Make sure you specify `restore=True` in the `metadata_collector.command` args.
* The restored arguments will not show up in the command arguments in the yml.
* Other arguments like `client`, `args` and so on can be added to the function declaration without problems.

##### Command with file output
If the command has a file output please specify `file_output=True` in the `@metadata_collector.command` args like so
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command", outputs_prefix="FunkyFile", file_output=True)
def funky_command():
    print("funk")
```
This will result in the following metadata for the command outputs:
```yaml
  commands:
  - deprecated: false
    description: ''
    name: funky-command
    arguments: []
    outputs:
    - contextPath: FunkyFile.EntryID
      description: The EntryID of the report file.
      type: Unknown
    - contextPath: FunkyFile.Extension
      description: The extension of the report file.
      type: String
    - contextPath: FunkyFile.Name
      description: The name of the report file.
      type: String
    - contextPath: FunkyFile.Info
      description: The info of the report file.
      type: String
    - contextPath: FunkyFile.Size
      description: The size of the report file.
      type: Number
    - contextPath: FunkyFile.Type
      description: The type of the report file.
      type: String
```

#### Metadata from `metadata_collector.command` inputs
In order to add command description, one can specify it in `@metadata_collector.command` under the description key like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command", description="Some funky command.")
def funky_command():
    print("funk")
```
##### InputArgument
To explicitly add input arguments use the `InputArgument` object like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command",
                            description="Very funky",
                            inputs_list=[InputArgument(name="some_name",
                                                       description="some description."),
                                         InputArgument(name="some_other_name",
                                                       description="some other description.")])
def funky_command():
    print("funk")
```
`InputArgument` arguments include the following:
```python
name, description, required, default, is_array, secret, execution, options, input_type
```
Where `options` and `input_type` behave similarly to those in the ConfKey:
`options` to specify predefined arguments with list of options, and `input_type` to specify an enum class as the
predefined options.

If `is_array` is not specified it is inferred from the `input_type` or defaults to `False`

##### OutputArgument
To explicitly add output arguments use the `OutputArgument` object like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command",
                            description="Very funky",
                            output_prefix="funk",
                            outputs_list=[OutputArgument(name="some_out",
                                                         description="some desc",
                                                         output_type=int),
                                          OutputArgument(name="some_other_name",
                                                         description="some other description.",
                                                         output_type=bool)])
def funky_command():
    print("funk")
```
`OutputArgument` arguments include the following:
```python
name, description, output_type, prefix
```
Where `output_type` will be converted from a python type to available context outputs types.

The output prefix in the context data will be the one specified in the `@metadata_collector.command`, for our example it will be `funk`.

###### Multiple prefixes
In order to have multiple prefixes specify the `multiple_output_prefixes=True` argument in the
`@metadata_collector.command` and add a `prefix` argument to every OutputArgument like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command",
                            description="Very funky",
                            multiple_output_prefixes=True,
                            outputs_list=[OutputArgument(name="some_out",
                                                         description="some desc",
                                                         output_type=int,
                                                         prefix="funky"),
                                          OutputArgument(name="some_other_name",
                                                         description="some other description.",
                                                         output_type=bool,
                                                         prefix="classy")])
def funky_command():
    print("funk")
```
If the `prefix` was not specified in the `OutputArgument` the general `outputs_prefix` provided in `@metadata_collector.command` is used.
If `outputs_prefix` is not defined, the `integration_name` provided in `YMLMetadataCollector` initialization is used.

#### Metadata from docstring and declaration
An alternative to specifing the command metadata in the `@metadata_collector.command` usage,
one can specify the description, the output arguments and the input arguments in the docstring of the function.
##### Description
To specify a description of the command in the docstring, use the first line (or lines) like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command."""
    print("funk")
```
The description will be `Very funky command.`.
Use an empty line to end the description. For example the description for the following command:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command():
    """The command is used to give up the funk.
    It is a very funky command.

    The function implementation though requires no funk.
    """
    print("funk")
```
will be `The command is used to give up the funk.\n     It is a very funky command.`.
##### Args
To specify input arguments use the `Args` section like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Args:
        beat: The beat to the funk.
        punk: The punk to the funk.
    """
    print("funk")
```
This will result in the following input argument metadata:
```yaml
    arguments:
    - name: beat
      isArray: false
      description: The beat to the funk.
      required: true
      secret: false
      default: false
    - name: punk
      isArray: false
      description: The punk to the funk.
      required: true
      secret: false
      default: false
```
To specify if the argument is an array or not, you can either add an argument type
in the docstring like so
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Args:
        beat (int): The beat to the funk.
        punk (str): The punk to the funk.
    """
    print("funk")
```
or specify it as a type in the function declaration like so
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command(beat: int, punk: str):
    """Very funky command.

    Args:
        beat: The beat to the funk.
        punk: The punk to the funk.
    """
    print("funk")
```

If your argument has predefined options, you can either add it as an enum class as the argument type like so
```python
class BeatOptions(enum.Enum):
    UpTown = "up_town"
    DownTown = "down_town"

@metadata_collector.command(command_name="funky-command")
def funky_command(beat: BeatOptions):
    """Very funky command.

    Args:
        beat: The beat to the funk.
    """
    print("funk")
```

Or equivalently:
```python
class BeatOptions(enum.Enum):
    UpTown = "up_town"
    DownTown = "down_town"

@metadata_collector.command(command_name="funky-command")
def funky_command(beat):
    """Very funky command.

    Args:
        beat (BeatOptions): The beat to the funk.
    """
    print("funk")
```

Or specify `options=[<option1>,<option2>, ...].` like so
```python
@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Args:
        beat: The beat to the funk. options=[up_town, down_town].
    """
    print("funk")
```

To specify default use `default=<The default>.` like so
```python
@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Args:
        punk: The punk to the funk. default=Avril Lavigne.
    """
    print("funk")
```
To specify the argument is a secret, add `secret.` to the argument description.
To specify execution=True, add `potentially harmful.` or `execution.` to the argument description.
To specify required=True, add `required.` to the argument description.
For example the following docstring:
```python
@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Args:
        punk: The punk to the funk. default=Avril Lavigne. secret. execution.
    """
    print("funk")
```
Will result in the following input argument metadata:
```yaml
    arguments:
    - name: punk
      isArray: false
      description: The punk to the funk.
      required: false
      secret: true
      default: true
      defaultValue: Avril Lavigne
      execution: true
```

##### Context Outputs
To specify command outputs use the `Context Outputs` section like so:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command")
def funky_command():
    """Very funky command.

    Context Outputs:
        song (str): A funky song.
    """
    print("funk")
```
This will result in the following metadata:
```yaml
  - deprecated: false
    description: Very funky command.
    name: funky-command
    arguments: []
    outputs:
    - contextPath: some_name.song
      description: A funky song.
      type: String
```

To add an output prefix for all context outputs of the command, use the `outputs_prefix` in the `@metadata_collector.command`.
###### Multiple prefixes
To specify multiple output prefixes in the docstring you can specify the `multiple_output_prefixes=True` in the `@metadata_collector.command`
and add the prefixes to the command names like so
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command", multiple_output_prefixes=True)
def funky_command():
    """Very funky command.

    Context Outputs:
        funky.song (str): A funky song.
        classy.song (str): An alternative classy song.
    """
    print("funk")
```
#### Notes
* Metadata from explicit `@metadata_collector.command` arguments can be used along with metadata providing in docstring, as long as it is not the same field.
For example, one can provide inputs_list via `@metadata_collector.command` and `Context Outputs` in the docstring, specifing both inputs and outputs.
* If a field is specified in both ways: explicitly in `@metadata_collector.command` and in the docstring, the explicit one will be used.
For example:
```python
metadata_collector = YMLMetadataCollector(integration_name="some_name")

@metadata_collector.command(command_name="funky-command",
                            description="Very funky")
def funky_command():
    """Very Classy"""
    print("func")
```
The description of the latter command will be `Very funky`.

## Hello World Example
Code:
```python
import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

import enum
import json
import urllib3
import dateparser
import traceback
from typing import Any, Dict, List, Optional, Union

# Disable insecure warnings
urllib3.disable_warnings()

''' CONSTANTS '''

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
MAX_INCIDENTS_TO_FETCH = 50
HELLOWORLD_SEVERITIES = ['Low', 'Medium', 'High', 'Critical']

# Starting with init of metadata_collector
metadata_collector = YMLMetadataCollector(integration_name="HelloWorldNoYML",
                                          description="This is the Hello World integration for getting started.",
                                          display="HelloWorldNoYML",
                                          category="Utilities",
                                          docker_image="demisto/python3:3.9.8.24399",
                                          is_fetch=True,
                                          long_running=False,
                                          long_running_port=False,
                                          is_runonce=False,
                                          integration_subtype="python3",
                                          integration_type="python",
                                          fromversion="5.0.0",
                                          default_mapper_in="HelloWorld-mapper",
                                          default_classifier="HelloWorld",
                                          conf=[ConfKey(name="url",
                                                        display="Server URL (e.g. https://soar.monstersofhack.com)",
                                                        required=True,
                                                        default_value="https://soar.monstersofhack.com"),
                                                ConfKey(name="isFetch",
                                                        display="Fetch incidents",
                                                        required=False,
                                                        key_type=ParameterTypes.BOOLEAN),
                                                ConfKey(name="incidentType",
                                                        display="Incident type",
                                                        required=False,
                                                        default_value="https://soar.monstersofhack.com",
                                                        key_type=ParameterTypes.SINGLE_SELECT),
                                                ConfKey(name="max_fetch",
                                                        display="Maximum number of incidents per fetch",
                                                        required=False,
                                                        default_value='10'),
                                                ConfKey(name="apikey",
                                                        display="API Key",
                                                        required=True,
                                                        key_type=ParameterTypes.TEXT_AREA_ENCRYPTED),
                                                ConfKey(name="threshold_ip",
                                                        display="Score threshold for IP reputation command",
                                                        required=False,
                                                        default_value='65',
                                                        additional_info="Set this to determine the HelloWorld score "
                                                                        "that will determine if an IP is malicious "
                                                                        "(0-100)"),
                                                ConfKey(name="threshold_domain",
                                                        display="Score threshold for domain reputation command",
                                                        required=False,
                                                        default_value='65',
                                                        additional_info="Set this to determine the HelloWorld score "
                                                                        "that will determine if a domain is malicious "
                                                                        "(0-100)"),
                                                ConfKey(name="alert_status",
                                                        display="Fetch alerts with status (ACTIVE, CLOSED)",
                                                        required=False,
                                                        default_value="ACTIVE",
                                                        options=["ACTIVE", "CLOSED"],
                                                        key_type=ParameterTypes.SINGLE_SELECT),
                                                ConfKey(name="alert_type",
                                                        display="Fetch alerts with type",
                                                        required=False,
                                                        additional_info="Comma-separated list of types of alerts to "
                                                                        "fetch. Types might change over time. Some "
                                                                        "examples are 'Bug' and 'Vulnerability'"),
                                                ConfKey(name="min_severity",
                                                        display="Minimum severity of alerts to fetch",
                                                        required=True,
                                                        default_value='Low',
                                                        options=["Low", "Medium", "High", "Critical"],
                                                        key_type=ParameterTypes.SINGLE_SELECT),
                                                ConfKey(name="first_fetch",
                                                        display="First fetch time",
                                                        required=False,
                                                        default_value="3 days"),
                                                ConfKey(name="insecure",
                                                        display="Trust any certificate (not secure)",
                                                        required=False,
                                                        key_type=ParameterTypes.BOOLEAN),
                                                ConfKey(name="proxy",
                                                        display="Use system proxy settings",
                                                        required=False,
                                                        key_type=ParameterTypes.BOOLEAN)
                                                ])

''' CLIENT CLASS '''


class Client(BaseClient):
    """Client class to interact with the service API

    This Client implements API calls, and does not contain any Demisto logic.
    Should only do requests and return data.
    It inherits from BaseClient defined in CommonServer Python.
    Most calls use _http_request() that handles proxy, SSL verification, etc.
    For this HelloWorld implementation, no special attributes defined
    """

    def get_ip_reputation(self, ip):
        """Gets the IP reputation using the '/ip' API endpoint

        :type ip: ``str``
        :param ip: IP address to get the reputation for

        :return: dict containing the IP reputation as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/ip',
            params={
                'ip': ip
            }
        )

    def get_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """Gets the Domain reputation using the '/domain' API endpoint

        :type domain: ``str``
        :param domain: domain name to get the reputation for

        :return: dict containing the domain reputation as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/domain',
            params={
                'domain': domain
            }
        )

    def search_alerts(self, alert_status: Optional[str], severity: Optional[str],
                      alert_type: Optional[str], max_results: Optional[int],
                      start_time: Optional[int]) -> List[Dict[str, Any]]:
        """Searches for HelloWorld alerts using the '/get_alerts' API endpoint

        All the parameters are passed directly to the API as HTTP POST parameters in the request

        :type alert_status: ``Optional[str]``
        :param alert_status: status of the alert to search for. Options are: 'ACTIVE' or 'CLOSED'

        :type severity: ``Optional[str]``
        :param severity:
            severity of the alert to search for. Comma-separated values.
            Options are: "Low", "Medium", "High", "Critical"

        :type alert_type: ``Optional[str]``
        :param alert_type: type of alerts to search for. There is no list of predefined types

        :type max_results: ``Optional[int]``
        :param max_results: maximum number of results to return

        :type start_time: ``Optional[int]``
        :param start_time: start timestamp (epoch in seconds) for the alert search

        :return: list containing the found HelloWorld alerts as dicts
        :rtype: ``List[Dict[str, Any]]``
        """

        request_params: Dict[str, Any] = {}

        if alert_status:
            request_params['alert_status'] = alert_status

        if alert_type:
            request_params['alert_type'] = alert_type

        if severity:
            request_params['severity'] = severity

        if max_results:
            request_params['max_results'] = max_results

        if start_time:
            request_params['start_time'] = start_time

        return self._http_request(
            method='GET',
            url_suffix='/get_alerts',
            params=request_params
        )

    def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """Gets a specific HelloWorld alert by id

        :type alert_id: ``str``
        :param alert_id: id of the alert to return

        :return: dict containing the alert as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/get_alert_details',
            params={
                'alert_id': alert_id
            }
        )

    def update_alert_status(self, alert_id: str, alert_status: str) -> Dict[str, Any]:
        """Changes the status of a specific HelloWorld alert

        :type alert_id: ``str``
        :param alert_id: id of the alert to return

        :type alert_status: ``str``
        :param alert_status: new alert status. Options are: 'ACTIVE' or 'CLOSED'

        :return: dict containing the alert as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/change_alert_status',
            params={
                'alert_id': alert_id,
                'alert_status': alert_status
            }
        )

    def scan_start(self, hostname: str) -> Dict[str, Any]:
        """Starts a HelloWorld scan on a specific hostname

        :type hostname: ``str``
        :param hostname: hostname of the machine to scan

        :return: dict containing the scan status as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/start_scan',
            params={
                'hostname': hostname
            }
        )

    def scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Gets the status of a HelloWorld scan

        :type scan_id: ``str``
        :param scan_id: ID of the scan to retrieve status for

        :return: dict containing the scan status as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/check_scan',
            params={
                'scan_id': scan_id
            }
        )

    def scan_results(self, scan_id: str) -> Dict[str, Any]:
        """Gets the results of a HelloWorld scan

        :type scan_id: ``str``
        :param scan_id: ID of the scan to retrieve results for

        :return: dict containing the scan results as returned from the API
        :rtype: ``Dict[str, Any]``
        """

        return self._http_request(
            method='GET',
            url_suffix='/get_scan_results',
            params={
                'scan_id': scan_id
            }
        )

    def say_hello(self, name: str) -> str:
        """Returns 'Hello {name}'

        :type name: ``str``
        :param name: name to append to the 'Hello' string

        :return: string containing 'Hello {name}'
        :rtype: ``str``
        """

        return f'Hello {name}'


''' HELPER FUNCTIONS '''


def parse_domain_date(domain_date: Union[List[str], str], date_format: str = '%Y-%m-%dT%H:%M:%S.000Z') -> Optional[str]:
    """Converts whois date format to an ISO8601 string

    Converts the HelloWorld domain WHOIS date (YYYY-mm-dd HH:MM:SS) format
    in a datetime. If a list is returned with multiple elements, takes only
    the first one.

    :type domain_date: ``Union[List[str],str]``
    :param date_format:
        a string or list of strings with the format 'YYYY-mm-DD HH:MM:SS'

    :return: Parsed time in ISO8601 format
    :rtype: ``Optional[str]``
    """

    if isinstance(domain_date, str):
        # if str parse the value
        domain_date_dt = dateparser.parse(domain_date)
        if domain_date_dt:
            return domain_date_dt.strftime(date_format)
    elif isinstance(domain_date, list) and len(domain_date) > 0 and isinstance(domain_date[0], str):
        # if list with at least one element, parse the first element
        domain_date_dt = dateparser.parse(domain_date[0])
        if domain_date_dt:
            return domain_date_dt.strftime(date_format)
    # in any other case return nothing
    return None


def convert_to_demisto_severity(severity: str) -> int:
    """Maps HelloWorld severity to Cortex XSOAR severity

    Converts the HelloWorld alert severity level ('Low', 'Medium',
    'High', 'Critical') to Cortex XSOAR incident severity (1 to 4)
    for mapping.

    :type severity: ``str``
    :param severity: severity as returned from the HelloWorld API (str)

    :return: Cortex XSOAR Severity (1 to 4)
    :rtype: ``int``
    """

    # In this case the mapping is straightforward, but more complex mappings
    # might be required in your integration, so a dedicated function is
    # recommended. This mapping should also be documented.
    return {
        'Low': IncidentSeverity.LOW,
        'Medium': IncidentSeverity.MEDIUM,
        'High': IncidentSeverity.HIGH,
        'Critical': IncidentSeverity.CRITICAL
    }[severity]


''' COMMAND FUNCTIONS '''


def test_module(client: Client, first_fetch_time: int) -> str:
    """Tests API connectivity and authentication'

    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.

    :type client: ``Client``
    :param Client: HelloWorld client to use

    :type name: ``str``
    :param name: name to append to the 'Hello' string

    :return: 'ok' if test passed, anything else will fail the test.
    :rtype: ``str``
    """

    # INTEGRATION DEVELOPER TIP
    # Client class should raise the exceptions, but if the test fails
    # the exception text is printed to the Cortex XSOAR UI.
    # If you have some specific errors you want to capture (i.e. auth failure)
    # you should catch the exception here and return a string with a more
    # readable output (for example return 'Authentication Error, API Key
    # invalid').
    # Cortex XSOAR will print everything you return different than 'ok' as
    # an error
    try:
        client.search_alerts(max_results=1, start_time=first_fetch_time, alert_status=None, alert_type=None,
                             severity=None)
    except DemistoException as e:
        if 'Forbidden' in str(e):
            return 'Authorization Error: make sure API Key is correctly set'
        else:
            raise e
    return 'ok'


# Example of decorated function with args and context outputs in docstirng.
@metadata_collector.command(command_name="helloworld-say-hello", outputs_prefix="HelloWorld")
def say_hello_command(client: Client, args: Dict[str, Any], **kwargs) -> CommandResults:
    """Hello command - prints hello to anyone.

    Args:
        client (Client): HelloWorld client to use.
        name (str):  The name of whom you want to say hello to.

    Returns:
        A ``CommandResults`` object that is then passed to ``return_results``,
        that contains the hello world message

    Context Outputs:
        hello (str): Should be Hello **something** here.

    """

    name = args.get('name', None)
    if not name:
        raise ValueError('name not specified')

    # Call the Client function and get the raw response
    result = client.say_hello(name)
    readable_output = f'## {result}'

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix='HelloWorld.hello',
        outputs_key_field='',
        outputs=result
    )


class SeverityEnum(enum.Enum):
    """YML configuration key types."""
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"


# Example of input arguments list and command outputs in docstring.
SEARCH_ALERTS_INPUTS = [InputArgument(name='severity',  # option 1
                                      description='Filter by alert severity. Comma-separated value '
                                                  '(Low,Medium,High,Critical)',
                                      input_type=SeverityEnum),
                        InputArgument(name='status',
                                      description='Filter by alert status.',
                                      options=['ACTIVE', 'CLOSED']),
                        InputArgument(name='alert_type',
                                      description='Filter by alert type.'),
                        InputArgument(name='max_results',
                                      description='Maximum results to return.'),
                        InputArgument(name='start_time',
                                      description='Filter by start time. \nExamples:\n  \"3 days ago\"\n  '
                                                  '\"1 month\"\n  \"2019-10-10T12:22:00\"\n  \"2019-10-10\"')]


@metadata_collector.command(command_name='helloworld-search-alerts', inputs_list=SEARCH_ALERTS_INPUTS,
                            outputs_prefix='HelloWorld.Alert')
def search_alerts_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """Search HelloWorld Alerts.

    :type client: ``Client``
    :param Client: HelloWorld client to use

    :type args: ``Dict[str, Any]``
    :param args:
        all command arguments, usually passed from ``demisto.args()``.
        ``args['status']`` alert status. Options are 'ACTIVE' or 'CLOSED'
        ``args['severity']`` alert severity CSV
        ``args['alert_type']`` alert type
        ``args['start_time']``  start time as ISO8601 date or seconds since epoch
        ``args['max_results']`` maximum number of results to return

    :return:
        A ``CommandResults`` object that is then passed to ``return_results``,
        that contains alerts

    :rtype: ``CommandResults``

    Context Outputs:
        alert_id (str): Alert ID.
        alert_status (str): Alert status. Can be 'ACTIVE' or 'CLOSED'.
        alert_type (str): Alert type. For example 'Bug' or 'Vulnerability'.
        created (datetime.datetime): Alert created time. Format is ISO8601 (i.e. '2020-04-30T10:35:00.000Z').
        name (str): Alert name.
        severity (str): Alert severity. Can be 'Low', 'Medium', 'High' or 'Critical'.
    """

    status = args.get('status')

    severities: List[str] = HELLOWORLD_SEVERITIES
    severity = args.get('severity', None)
    if severity:
        severities = severity.split(',')
        if not all(s in HELLOWORLD_SEVERITIES for s in severities):
            raise ValueError(
                f'severity must be a comma-separated value '
                f'with the following options: {",".join(HELLOWORLD_SEVERITIES)}')

    alert_type = args.get('alert_type')

    start_time = arg_to_datetime(
        arg=args.get('start_time'),
        arg_name='start_time',
        required=False
    )

    max_results = arg_to_number(
        arg=args.get('max_results'),
        arg_name='max_results',
        required=False
    )

    alerts = client.search_alerts(
        severity=','.join(severities),
        alert_status=status,
        alert_type=alert_type,
        start_time=int(start_time.timestamp()) if start_time else None,
        max_results=max_results
    )

    for alert in alerts:
        if 'created' not in alert:
            continue
        created_time_ms = int(alert.get('created', '0')) * 1000
        alert['created'] = timestamp_to_datestring(created_time_ms)

    return CommandResults(
        outputs_prefix='HelloWorld.Alert',
        outputs_key_field='alert_id',
        outputs=alerts
    )


# Example of outputs dict and reuse of outputs_prefix
GET_ALERT_OUTPUTS = [OutputArgument(name='alert_id', output_type=str, description='Alert ID.'),
                     OutputArgument(name='created', output_type=datetime,
                                    description="Alert created time. Format is ISO8601 "
                                                "(i.e. '2020-04-30T10:35:00.000Z').")]


@metadata_collector.command(command_name='helloworld-get-alert', outputs_prefix='HelloWorld.Alert',
                            outputs_list=GET_ALERT_OUTPUTS, restore=True)
def get_alert_command(client: Client, args: Dict[str, Any], outputs_prefix) -> CommandResults:
    """Retrieve alert extra data by ID.

    :type client: ``Client``
    :param Client: HelloWorld client to use

    :param alert_id: alert ID to return

    :return:
        A ``CommandResults`` object that is then passed to ``return_results``,
        that contains an alert

    :rtype: ``CommandResults``
    """

    alert_id = args.get('alert_id', None)
    if not alert_id:
        raise ValueError('alert_id not specified')

    alert = client.get_alert(alert_id=alert_id)

    if 'created' in alert:
        created_time_ms = int(alert.get('created', '0')) * 1000
        alert['created'] = timestamp_to_datestring(created_time_ms)

    readable_output = tableToMarkdown(f'HelloWorld Alert {alert_id}', alert)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix=outputs_prefix,
        outputs_key_field='alert_id',
        outputs=alert
    )


# option 3
class StatusEnum(enum.Enum):
    """YML configuration key types."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


# Complicated args in docstring example. (required and options tags)
@metadata_collector.command(command_name='helloworld-update-alert-status', outputs_prefix='HelloWorld.Alert')
def update_alert_status_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """Update the status for an alert.

    Changes the status of a HelloWorld alert and returns the updated alert info

    Args:
        client (Client): HelloWorld client to use.
        alert_id: required. Alert ID to update.
        status (StatusEnum): required. New status of the alert. Options=[ACTIVE, CLOSED].

    Returns:
       A ``CommandResults`` object that is then passed to ``return_results``,
        that contains an updated alert.

    Context Outputs:
        alert_id (str): Alert ID.
        updated (datetime): Alert update time. Format is ISO8601 (i.e. '2020-04-30T10:35:00.000Z').
        alert_status (str): Alert status. Can be 'ACTIVE' or 'CLOSED'.
    """

    alert_id = args.get('alert_id', None)
    if not alert_id:
        raise ValueError('alert_id not specified')

    status = args.get('status', None)
    if status not in ('ACTIVE', 'CLOSED'):
        raise ValueError('status must be either ACTIVE or CLOSED')

    alert = client.update_alert_status(alert_id, status)

    if 'updated' in alert:
        updated_time_ms = int(alert.get('updated', '0')) * 1000
        alert['updated'] = timestamp_to_datestring(updated_time_ms)

    readable_output = tableToMarkdown(f'HelloWorld Alert {alert_id}', alert)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix='HelloWorld.Alert',
        outputs_key_field='alert_id',
        outputs=alert
    )


def scan_results_command(client: Client, args: Dict[str, Any]) ->\
        Union[Dict[str, Any], CommandResults, List[CommandResults]]:
    """helloworld-scan-results command: Returns results for a HelloWorld scan

    :type client: ``Client``
    :param Client: HelloWorld client to use

    :type args: ``Dict[str, Any]``
    :param args:
        all command arguments, usually passed from ``demisto.args()``.
        ``args['scan_id']`` scan ID to retrieve results
        ``args['format']`` format of the results. Options are 'file' or 'json'

    :return:
        A ``CommandResults`` compatible to return ``return_results()``,
        that contains a scan result when json format is selected, or
        A Dict of entries also compatible to ``return_results()`` that
        contains the output file when file format is selected.

    :rtype: ``Union[Dict[str, Any],CommandResults]``
    """

    scan_id = args.get('scan_id', None)
    if not scan_id:
        raise ValueError('scan_id not specified')

    scan_format = args.get('format', 'file')

    results = client.scan_results(scan_id=scan_id)
    if scan_format == 'file':
        return (
            fileResult(
                filename=f'{scan_id}.json',
                data=json.dumps(results, indent=4),
                file_type=entryTypes['entryInfoFile']
            )
        )
    elif scan_format == 'json':
        cves: List[Common.CVE] = []
        command_results: List[CommandResults] = []
        entities = results.get('entities', [])
        for e in entities:
            if 'vulns' in e.keys() and isinstance(e['vulns'], list):
                cves.extend(
                    [Common.CVE(id=c, cvss=None, published=None, modified=None, description=None) for c in e['vulns']])

        readable_output = tableToMarkdown(f'Scan {scan_id} results', entities)
        command_results.append(CommandResults(
            readable_output=readable_output,
            outputs_prefix='HelloWorld.Scan',
            outputs_key_field='scan_id',
            outputs=results
        ))

        cves = list(set(cves))  # make the indicator list unique
        for cve in cves:
            command_results.append(CommandResults(
                readable_output=f"CVE {cve}",
                indicator=cve
            ))
        return command_results
    else:
        raise ValueError('Incorrect format, must be "json" or "file"')


''' MAIN FUNCTION '''


def main() -> None:
    """main function, parses params and runs command functions

    :return:
    :rtype:
    """

    api_key = demisto.params().get('apikey')

    base_url = urljoin(demisto.params()['url'], '/api/v1')

    verify_certificate = not demisto.params().get('insecure', False)

    first_fetch_time = arg_to_datetime(
        arg=demisto.params().get('first_fetch', '3 days'),
        arg_name='First fetch time',
        required=True
    )
    first_fetch_timestamp = int(first_fetch_time.timestamp()) if first_fetch_time else None
    assert isinstance(first_fetch_timestamp, int)
    proxy = demisto.params().get('proxy', False)

    demisto.debug(f'Command being called is {demisto.command()}')
    try:
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        client = Client(
            base_url=base_url,
            verify=verify_certificate,
            headers=headers,
            proxy=proxy)

        if demisto.command() == 'test-module':
            result = test_module(client, first_fetch_timestamp)
            return_results(result)

        elif demisto.command() == 'helloworld-say-hello':
            return_results(say_hello_command(client, demisto.args()))

        elif demisto.command() == 'helloworld-search-alerts':
            return_results(search_alerts_command(client, demisto.args()))

        elif demisto.command() == 'helloworld-get-alert':
            return_results(get_alert_command(client, demisto.args()))

        elif demisto.command() == 'helloworld-update-alert-status':
            return_results(update_alert_status_command(client, demisto.args()))

    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {demisto.command()} command.\nError:\n{str(e)}')


''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
                                                ])
```

Result:
```yaml
category: Utilities
description: This is the Hello World integration for getting started.
commonfields:
  id: HelloWorldNoYML
  version: -1
name: HelloWorldNoYML
display: HelloWorldNoYML
configuration:
- display: Server URL (e.g. https://soar.monstersofhack.com)
  name: url
  type: 0
  required: true
  defaultvalue: https://soar.monstersofhack.com
- display: Fetch incidents
  name: isFetch
  type: 8
  required: false
- display: Incident type
  name: incidentType
  type: 15
  required: false
  defaultvalue: https://soar.monstersofhack.com
- display: Maximum number of incidents per fetch
  name: max_fetch
  type: 0
  required: false
  defaultvalue: '10'
- display: API Key
  name: apikey
  type: 14
  required: true
- display: Score threshold for IP reputation command
  name: threshold_ip
  type: 0
  required: false
  defaultvalue: '65'
  additionalinfo: Set this to determine the HelloWorld score that will determine if
    an IP is malicious (0-100)
- display: Score threshold for domain reputation command
  name: threshold_domain
  type: 0
  required: false
  defaultvalue: '65'
  additionalinfo: Set this to determine the HelloWorld score that will determine if
    a domain is malicious (0-100)
- display: Fetch alerts with status (ACTIVE, CLOSED)
  name: alert_status
  type: 15
  required: false
  defaultvalue: ACTIVE
  options:
  - ACTIVE
  - CLOSED
- display: Fetch alerts with type
  name: alert_type
  type: 0
  required: false
  additionalinfo: Comma-separated list of types of alerts to fetch. Types might change
    over time. Some examples are 'Bug' and 'Vulnerability'
- display: Minimum severity of alerts to fetch
  name: min_severity
  type: 15
  required: true
  defaultvalue: Low
  options:
  - Low
  - Medium
  - High
  - Critical
- display: First fetch time
  name: first_fetch
  type: 0
  required: false
  defaultvalue: 3 days
- display: Trust any certificate (not secure)
  name: insecure
  type: 8
  required: false
- display: Use system proxy settings
  name: proxy
  type: 8
  required: false
script:
  commands:
  - deprecated: false
    description: Retrieve alert extra data by ID.
    name: helloworld-get-alert
    arguments: []
    outputs:
    - contextPath: HelloWorld.Alert.alert_id
      description: Alert ID.
      type: String
    - contextPath: HelloWorld.Alert.created
      description: Alert created time. Format is ISO8601 (i.e. '2020-04-30T10:35:00.000Z').
      type: Unknown
  - deprecated: false
    description: Hello command - prints hello to anyone.
    name: helloworld-say-hello
    arguments:
    - name: name
      isArray: false
      description: The name of whom you want to say hello to.
      required: true
      secret: false
      default: false
    outputs:
    - contextPath: HelloWorld.hello
      description: Should be Hello **something** here.
      type: String
  - deprecated: false
    description: Search HelloWorld Alerts.
    name: helloworld-search-alerts
    arguments:
    - name: severity
      isArray: false
      description: Filter by alert severity. Comma-separated value (Low,Medium,High,Critical)
      required: true
      secret: false
      default: false
      predefined:
      - Low
      - Medium
      - High
      - Critical
      auto: PREDEFINED
    - name: status
      isArray: false
      description: Filter by alert status.
      required: true
      secret: false
      default: false
      predefined:
      - ACTIVE
      - CLOSED
      auto: PREDEFINED
    - name: alert_type
      isArray: false
      description: Filter by alert type.
      required: true
      secret: false
      default: false
    - name: max_results
      isArray: false
      description: Maximum results to return.
      required: true
      secret: false
      default: false
    - name: start_time
      isArray: false
      description: "Filter by start time. \nExamples:\n  \"3 days ago\"\n  \"1 month\"\
        \n  \"2019-10-10T12:22:00\"\n  \"2019-10-10\""
      required: true
      secret: false
      default: false
    outputs:
    - contextPath: HelloWorld.Alert.alert_id
      description: Alert ID.
      type: String
    - contextPath: HelloWorld.Alert.alert_status
      description: Alert status. Can be 'ACTIVE' or 'CLOSED'.
      type: String
    - contextPath: HelloWorld.Alert.alert_type
      description: Alert type. For example 'Bug' or 'Vulnerability'.
      type: String
    - contextPath: HelloWorld.Alert.created
      description: Alert created time. Format is ISO8601 (i.e. '2020-04-30T10:35:00.000Z').
      type: Date
    - contextPath: HelloWorld.Alert.name
      description: Alert name.
      type: String
    - contextPath: HelloWorld.Alert.severity
      description: Alert severity. Can be 'Low', 'Medium', 'High' or 'Critical'.
      type: String
  - deprecated: false
    description: Update the status for an alert.
    name: helloworld-update-alert-status
    arguments:
    - name: alert_id
      isArray: false
      description: Alert ID to update.
      required: true
      secret: false
      default: false
    - name: status
      isArray: false
      description: New status of the alert. Options=[ACTIVE, CLOSED].
      required: true
      secret: false
      default: false
      predefined:
      - ACTIVE
      - CLOSED
      auto: PREDEFINED
    outputs:
    - contextPath: HelloWorld.Alert.alert_id
      description: Alert ID.
      type: String
    - contextPath: HelloWorld.Alert.updated
      description: Alert update time. Format is ISO8601 (i.e. '2020-04-30T10:35:00.000Z').
      type: Unknown
    - contextPath: HelloWorld.Alert.alert_status
      description: Alert status. Can be 'ACTIVE' or 'CLOSED'.
      type: String
  script: '-'
  type: python
  subtype: python3
  dockerimage: demisto/python3:3.9.8.24399
  feed: false
  isfetch: true
  runonce: false
  longRunning: false
  longRunningPort: false
fromversion: 5.0.0
tests:
- No tests
defaultclassifier: HelloWorld
defaultmapperin: HelloWorld-mapper
```
