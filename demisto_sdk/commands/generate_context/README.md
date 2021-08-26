## generate-context
Generate a README file for an Integration, Script or a Playbook.

**Use-Cases**
This command is used to generate context paths automatically from an example file directly into an integration yml file.

**Arguments**:
* **-i, --input**
  Path of the yml file (ouputs are inserted here in-palce).
* **-e, --examples**
  Integrations: path for file containing command examples. Each command should be in a separate line.
* **--insecure**
  Skip certificate validation.
* **-v, --verbose**
  Verbose output - mainly for debugging purposes.

**Notes**
* The output of the command will be writen in the input file (in-place).

### Examples
```
demisto-sdk generate-context -i Packs/MyPack/Integrations/MyInt/MyInt.yml -e Packs/MyPack/Integrations/MyInt/command_exmaple.txt
```
This will generate the outputs contexts for all the commands in the example file.
