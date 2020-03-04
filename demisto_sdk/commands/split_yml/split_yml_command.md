## split-yml
Split a Demisto downloaded yml file(Of an integration or a script) and split it into multiple files so it will be in
the package format - https://demisto.pan.dev/docs/package-dir

**Use-Cases**
Our work in the Content repository is done in the package format, which enables us to preform more validations on our
code.
In turn those validation helps us maintain a more stable code base.

**Arguments**:
* **-i INFILE, --infile INFILE**
The yml file to extract from
* **-o OUTFILE, --outfile OUTFILE**
The output file or dir (if doing migrate) to write the code to
* **-m, --migrate**
Migrate an integration to package format. Pass to -o option a directory in this case.
* **-t {script,integration}, --type {script,integration}**
Yaml type. If not specified will try to determine type based upon path.
* **-d {True,False}, --demistomock {True,False}**
Add an import for demisto mock, true by default
* **-c {True,False}, --commonserver {True,False}**
Add an import for CommonServerPython. If not specified will import unless this is CommonServerPython

**Examples**
`demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)
</br></br>

`demisto-sdk split-yml -i Scripts/script-MyInt.yml -o Scripts/MyInt -m`
This will split the yml file to a directory with the script components (code, description, pipfile etc.)
