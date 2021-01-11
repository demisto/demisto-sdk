## generate-docs
Generate a README file for an Integration, Script or a Playbook.

**Use-Cases**
This command is used to create a documentation file for Cortex XSOAR content files.

**Arguments**:
* **-i, --input**Path of the yml file.
* **-o, --output** The output dir to write the documentation file into, documentation file name is README.md. If not specified, will be in the yml dir.
* **-u, --use_cases** For integration - Top use-cases. Number the steps by '*' (i.e. '\* foo. * bar.').
* **-e, --examples** Integrations: path for file containing command examples. Each command should be in a separate line.
  Scripts: the script example surrounded by quotes. For example: `-e '!ConvertFile entry_id=<entry_id>'`
* **-p, --permissions** permissions in the documentation.
* **-cp, --command_permissions** Path for file containing commands permissions. Each command permissions should be in a separate line (i.e. 'command-name Administrator READ-WRITE').
* **-l, --limitations** Known limitations. Number the steps by '*' (i.e. '\* foo. * bar.').
* **-id, --id_set** Path of updated id_set.json file.
* **--insecure** Skip certificate validation.
* **-v, --verbose** Verbose output - mainly for debugging purposes.

**Notes**
* If `command_permissions` wil not be given, a generic message regarding the need of permissions will be given.
* If no `output` given, the README.md file will be generated in the `input` file repository.
