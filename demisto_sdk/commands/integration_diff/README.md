## integration-diff
Check the differences between two versions of an integration and return a report of missing and changed elements in the new version.

### Use-Cases
This command is used to identify missing or modified details in a new integration version. This is useful when
developing a new version of an integration, and you want to make sure that all old integration version commands/arguments/outputs
exist in the new version. Running this command will give you a detailed report about all the missing or changed commands/arguments/outputs.

### Arguments
* **-n, --new**

    The path to the new integration yml file.

* **-o**, **--old**

    The path to the old integration yml file.

* **--docs-format**
    
    Whether output should be in the format for the version differences section in README

### Examples
`demisto-sdk integration-diff -n Packs/MyPack/Integrations/MyIntegration_v2/MyIntegration_v2.yml -o Packs/MyPack/Integrations/MyIntegration/MyIntegration.yml`
This will return you a report of all the missing commands/arguments/outputs in the new integration version, and 'The integrations are backward compatible' if no missing details were found.
