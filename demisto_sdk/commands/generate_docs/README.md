## generate-docs

### Overview

Generates a `README` file for your integration, script or playbook. Used to create documentation files for Cortex XSOAR.

This command creates a new README.md file in the same directory as the entity on which it ran, unless otherwise specified using the -o flag.
To generate command examples, set up the required environment variables prior to running this command in order to establish a connection between the Demisto SDK and the server, as well as create a file containing command examples to be run for the documentation.
>Note: This command is not supported in Cortex XSIAM.
### Options

* **-i, --input**
Path of the yml file.
* **-o, --output**
The output directory to write the documentation file to. Documentation file name is README.md. If not specified, written to the YAML directory.
* **-uc, --use_cases**
For integrations - provide a list of use-cases that should appear in the generated docs. Create an unordered list by using * before each use-case (i.e. '\* foo. * bar.').
* **-c, --command**
A comma-separated list of command names to generate documentation for. The rest of the commands are ignored. e.g xdr-get-incidents,xdr-update-incident
* **-e, --examples**
Integrations: Path for a file containing examples. Each command should be in a separate line or a comma-separated list of commands.
Scripts: the script example surrounded by quotes. For example: -e '!ConvertFile entry_id=<entry_id>'
* **-p, --permissions**
The needed permissions.
* **-cp, --command-permissions**
Path for file containing commands permissions. Each command permissions should be in a separate line (i.e. 'command-name Administrator READ-WRITE').
* **-l, --limitations**
Known limitations. Create an unordered list by using * before each use-case. (i.e. '\* foo. * bar.').
* **--insecure**
Skip certificate validation.
* **--old-version**
Path of the old integration version YML file.
* **--skip-breaking-changes**
Do not generate the breaking changes section.
* **-gr/-ngr, --graph/--no-graph**
Whether to use the content graph.
* **-f, --force**
Whether to force the generation of documentation (rather than update when it exists in version control).
* **--custom-image-path**
A custom path to a playbook image. If not stated, a default link will be added to the file.
* **-rt, --readme-template**
The readme template that should be appended to the given README.md file. Possible values: "syslog", "xdrc", "http-collector".

### Notes
- If `command_permissions` are not provided, a generic message regarding the need for permissions is given.

- If no `output` is provided, the README.md file is generated in the `input` file repository.

- If no `additionalinfo` is provided for a commonly used parameter (for example, API Key), a matching default value is used, see the parameters and defaults in `default_additional_information.json`.

- To generate an incident mirroring section, verify the `isremotesyncin` and/or `isremotesyncout` parameters are set to true in the YAML file. In addition, the following configuration parameters (if used) should be named as stated:

  - incidents_fetch_query
  - mirroring tags - available names are comment_tag, work_notes_tag and file_tag.
  - mirror_direction
  - close_incident
  - close_out (opposite of close_incident)

- If the integration/script/playbook exists in version control, the version from the main branch (the master) will be used to only render the modified sections (for example configuration, commands) unless the `--force flag` is specified.


### Examples

```bash
demisto-sdk generate-docs -i Packs/MyPack/Integrations/MyInt/MyInt.yml -e Packs/MyPack/Integrations/MyInt/command_example.txt
```

Generate a documentation for the `MyInt` integration using the command examples found in the .txt file in the `MyInt` integration.

```bash
demisto-sdk generate-docs -i Packs/MyPack/Integrations/MyInt/MyInt_v2.yml --old-version Packs/MyPack/Integrations/MyInt/MyInt.yml
```

Generate a documentation for `MyInt_v2` integration including a section about changes compared the `MyInt` integration.
The command will automatically detect if the given integration is a v2 using the integration's display name and create the changes section.
If no `--old-version` is supplied a prompt will appear asking for the path to the old integration.
