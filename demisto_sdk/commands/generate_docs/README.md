## generate-docs
Generate a README file for an Integration, Script or a Playbook.

**Use-Cases**
This command is used to create a documentation file for Cortex XSOAR content files.

**Arguments**:
* **-i, --input**
Path of the yml file.
* **-o, --output**
The output dir to write the documentation file into, documentation file name is README.md. If not specified, will be in the yml dir.
* **-uc, --use_cases**
For integration - Top use-cases. Number the steps by '*' (i.e. '\* foo. * bar.').
* **-c, --command**
A comma-separated command names to generate doc for, will ignore the rest of the commands. e.g xdr-get-incidents,xdr-update-incident
* **-e, --examples**
Integrations: path for file containing command examples. Each command should be in a separate line.
  Scripts: the script example surrounded by quotes. For example: `-e '!ConvertFile entry_id=<entry_id>'`
* **-p, --permissions**
Permissions in the documentation.
* **-cp, --command-permissions**
Path for file containing commands permissions. Each command permissions should be in a separate line (i.e. 'command-name Administrator READ-WRITE').
* **-l, --limitations**
Known limitations. Number the steps by '*' (i.e. '\* foo. * bar.').
* **--insecure**
Skip certificate validation.
* **-v, --verbose**
Verbose output - mainly for debugging purposes.
* **--old-version**
Path of the old integration version yml file.
* **--skip-breaking-changes**
Skip generating of breaking changes section.

**Notes**
* If `command_permissions` wil not be given, a generic message regarding the need of permissions will be given.
* If no `output` given, the README.md file will be generated in the `input` file repository.

### Examples
```
demisto-sdk generate-docs -i Packs/MyPack/Integrations/MyInt/MyInt.yml -e Packs/MyPack/Integrations/MyInt/command_exmaple.txt
```
This will generate a documentation for the MyInt integration using the command examples found in the .txt file in the MyInt integration.

```
demisto-sdk generate-docs -i Packs/MyPack/Integrations/MyInt/MyInt_v2.yml --old-version Packs/MyPack/Integrations/MyInt/MyInt.yml
```
This will generate a documentation for MyInt_v2 integration including a section about changes compared the MyInt integration.
The command will automatically detect if the given integration is a v2 using the integration's display name and create the changes section.
If no '--old-version' is supplied a prompt will appear asking for the path to the old integration.
