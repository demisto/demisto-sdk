## Generate YML from Python
### Overview
Generate YML file from Python code that includes special syntax.
The output file name will be the same as the Python code with the `.yml` extension instead of `.py`.
The generation currently supports integrations only.

The feature is supported from content Base pack version 1.20.0 and on.

### Options
* **-i, --input**
   (Required) The path to the python code to generate from.
* **-f, --force**
   Override existing yml file. If not used and yml file already exists, the script will not generate a new yml file.

For syntax and usage information see docs [here](https://docs-cortex.paloaltonetworks.com/r/1/Demisto-SDK-Guide/generate-yml-from-python)
