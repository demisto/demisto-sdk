## generate-unit-tests
Generate unit tests for an integration.
To use this command, install demisto-sdk with `pip install demisto-sdk[generate-unit-tests]`.

**Use-Cases**
This command is used to generate unit tests automatically from an integration python code.
Also supports generating unit tests for specific commands.
**Important**: this command is not intended to fully replace the manual work on unit tests but to ease the initial effort in writing them.

**Arguments**:
* *-i, --input_path*
  Path of the integration python file. (Mandatory)
* *-c, --commands*
  Specific commands name to generate unit test for (e.g. xdr-get-incidents).
* *-o, --output_dir*
  Directory to store the command output (generated test file) in (default is the input integration directory).
* *-clt, --console_log_threshold*
  Minimum logging threshold for the console logger.  [default: INFO]
* *-flt --file_log_threshold*
  Minimum logging threshold for the file logger. [default: DEBUG]
* *-lp, --log_file_path*
  Path to the log file. Default: ./demisto_sdk_debug.log. [default: ./demisto_sdk_debug.log]
* *-e, --examples*
  One of the following:
  - A path for a file containing Integration command examples. Each command example should be in a separate line.
  - A comma-separated list of examples, wrapped by quotes.
  If the file or the list contains a command with more than one example, all of them will be used as different test cases.
* *-d, --use_demisto*
  If passed, the XSOAR instance configured in the `DEMISTO_BASE_URL` and `DEMISTO_API_KEY` environment variables will run the Integration commands and generate outputs which will be used as mock outputs. **If this flag is not passed, you will need to create the mocks manually, at the outputs directory, with the name of the command.**
* *--insecure*
  Skip certificate validation when authorizing XSOAR.
* *-a, --append* Append the generated unit tests to an existing file (only if already exists).


**Notes**
* The outputs from the command run will be writen in an output file in the given directory.

**Required Code Conventions**
* Every command method name must have the suffix `_command`.
* Every command method must have the `args` dictionary parameter.
* Each argument access in `args` must be made using the `get()` method.
* Every command method must have the `client` parameter which must be typed (`client: Client`, where `Client` extends `BaseClient`).
* Each HTTP request made during the flow of the command must be done using the `_http_request()` method. (`method` must be passed).
* Every command must return a `CommandResults` object.
* Client class must include `__init__` function.
* Client class `__init__` function arguments have to include types (None will be passed otherwise).


**Test Data Files**
For the unit tests to run successfully, a `test_data` folder must exist and include:

* ***outputs*** folder - contains a JSON file for each HTTP request with a mock response (the file name should be the name of the client function making the HTTP call).
* ***outputs command files*** - if the `--use_demisto` flag was not given, outputs files must be provided for each command. File names should have the same name of the command. See examples files below to view the desired structure for the file.

**Command Examples file** -
For the command to work as planned, a `command_examples` file must be provided.

### Examples

#### Command Executions

```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -d --insecure
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -o Packs/MyPack/Integrations/MyInt
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -c MyInt_example_command
```

#### `command_examples` File

```text
!malwarebazaar-samples-list sample_type=tag sample_value=test limit=2
!malwarebazaar-samples-list sample_type=tag1 sample_value=test2 limit=444
!malwarebazaar-download-sample sha256_hash=1234
!file file=1234
!malwarebazaar-comment-add comment="test" sha256_hash=1234
```

#### Command Output File
##### malwarebazaar_comment_add_command.json
```json
{"readable_output": "Comment added to 1234 malware sample successfully",
  "outputs": {"comment": "test", "sha256_hash": "1234"}}
```
