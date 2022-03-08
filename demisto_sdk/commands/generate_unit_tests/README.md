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
* *-i, --input*
  Path of the integration python file.


**Notes**
* The output of the command will be writen in an output file in the given directory.

### Examples
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py 
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -o Packs/MyPack/Integrations/MyInt
```
```
demisto-sdk generate-unit-tests -i Packs/MyPack/Integrations/MyInt/MyInt.py -c 
```
