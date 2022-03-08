## generate-unit-tests
Generate unit tests for an integration.

**Use-Cases**
This command is used to generate unit tests automatically from an  integration python code.
Also supports generating unit tests for specific commands.

**Arguments**:
* *-c, --command*
  Specific commands name to generate unit test for (e.g. xdr-get-incidents).
* *-o, --output_dir*
  Directory to store the output in (default is current working directory).
* *-v, --verbose*
  Verbose output - mainly for debugging purposes
* *-i, --input_path*
  Path of the integration python file.


**Notes**
* The output of the command will be writen in an output file in the given directory.

**Code Conventions**
* Command name must contain "__command"_ prefix.
* Command must get _args_ as input (dictionary names _args_ contains all arguments required).
* Each args access must be made using _get_ method.
* Command must get _client_ as input and must be typed.
* Command must return CommandResults object.
* Each request made during the flow of the command must be done using _http_request_ method and include _method_ keyword, and _url_suffix_ keyword if needed.
* Client class must extend _BaseClass_


**Test Data Files**   
For the command work as planned test_data folder must include the following:   

***inputs folder*** - contains a json file for each command with mock arguments as inputs (dictionary). 
If more than 1 dictionary is given, an additional key sould be added: _parametrize_ with value _"True"_,
and each case must be preceded with _case#_ as key.

***outputs folder*** - contains a json file for each request made with mock response.


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

####input file

```json
{
  "parametrize" : "True",
  "case 1": {
  "sha256_hash": "value_test1",
  "comment": "comment_test1"
  },
  "case 2": {
  "sha256_hash": "value_test2",
  "comment": "comment_test2"
  }
}
```