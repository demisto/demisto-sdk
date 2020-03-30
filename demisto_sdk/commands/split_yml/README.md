## split-yml
Split a Demisto downloaded yml file(Of an integration or a script) and split it into multiple files so it will be in
the package format - https://demisto.pan.dev/docs/package-dir

**Use-Cases**
Our work in the Content repository is done in the package format, which enables us to preform more validations on our
code.
In turn those validation helps us maintain a more stable code base.

**Arguments**:
* **-i, --input**
The yml file to extract from
* **-o, --output**
The output dir to write the extracted code/description/image to
* **---no-demisto-mock {True,False}**
Don't add an import for demisto mock, false by default
**--no-common-server {True,False}**
Don't add an import for CommonServerPython, false by default

**Examples**
1. `demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

2. `demisto-sdk split-yml -i Scripts/script-MyInt.yml -o Scripts/MyInt`
This will split the yml file to a directory with the script components (code, description, pipfile etc.)
