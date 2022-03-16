## generate-unit-tests
Generate unit tests for an integration.

**Use-Cases**
This command is used to generate unit tests automatically from an  integration python code.
Also supports generating unit tests for specific commands.

**Arguments**:
* *-i, --input_path*
  Path of the integration python file. (Mandatory)
* *-c, --commands*
  Specific commands name to generate unit test for (e.g. xdr-get-incidents).
* *-o, --output_dir*
  Directory to store the output in (default is current working directory).
* *-v, --verbose*
  Verbose output - mainly for debugging purposes, logging level will be displayed accordingly.
* *-q, --quiet*
  Quiet output, only output results in the end.
* *-ql, --log-path*
  Path to store all levels of logs.
* *-td, --test_data_path*
  Path to test data directory.
* *--insecure*
  Skip certificate validation.
* *-e, --examples* One of the following:
  - Path for a file containing examples. Each command should be in a separate line.
  - Comma separated list of examples, wrapped by quotes.  
  If the file or list contains a command with more than one example, all of them will be used.


**Notes**
* The output of the command will be writen in an output file in the given directory.

**Code Conventions**
* Command name must contain *"_command"* prefix.
* Command must get *args* as input (dictionary names _args_ contains all arguments required).
* Each args access must be made using *get* method.
* Command must get *client* as input and must be typed.
* Command must return CommandResults object.
* Each request made during the flow of the command must be done using _http_request_ method and include _method_ keyword, and _url_suffix_ keyword if needed.
* Client class must extend *BaseClass*


**Test Data Files**   
For the the unit tests to work as planned test_data folder must include the following:   

***outputs folder*** - contains a json file for each request made with mock response (the name of the file should be as the name of the client function).
***outputs command files*** - if use_demisto option was not selected, outputs files must be provided for each command, with the name of the command, see at the examples files below the desired formation for the file.

**Command Examples file** - 
For the command to work as planned a command_examples file must be included.

### Examples

####command excecution

```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py 
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -o Packs/MyPack/Integrations/MyInt
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -c MyInt_example_command
```

####command-examples file

```text
!malwarebazaar-samples-list sample_type=tag sample_value=test limit=2
!malwarebazaar-samples-list sample_type=tag1 sample_value=test2 limit=444
!malwarebazaar-download-sample sha256_hash=1234
!file file=1234
!malwarebazaar-comment-add comment="test" sha256_hash=1234
```

####command output file
```json
{"readable_output": "Comment added to 094fd325049b8a9cf6d3e5ef2a6d4cc6a567d7d49c35f8bb8dd9e3c6acf3d78d malware sample successfully",
  "outputs": {"comment": "test", "sha256_hash": "094fd325049b8a9cf6d3e5ef2a6d4cc6a567d7d49c35f8bb8dd9e3c6acf3d78d"}}
```