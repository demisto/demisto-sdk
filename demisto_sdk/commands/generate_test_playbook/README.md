### Generate Test Playbook

Generate Test Playbook from integration/script yml
**Arguments**:
* **-i, --input**
   Specify integration/script yml path (must be a valid yml file)
* **-o, --output**
   Specify output directory or path. If not specified, and the input is located at `.../Packs/<pack_name>/Integrations`, the output is saved under `.../Packs/<pack_name>/TestPlaybooks`. If no folder in the input hierarchy is named Packs, the output is saved in the current directory.
* **-n, --name**
   Specify test playbook name, the output file name will be `playbook-<name>_Test.yml`
* **--no-outputs**
   Skip generating verification conditions for each output contextPath. Use when you want to decide which outputs to verify and which not
* **-v, --verbose**
   Verbose output for debug purposes - shows full exception stack trace

**Examples**:
`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -o TestPlaybooks`
Will create a test playbook in TestPlaybook folder, with filename `playbook-TestXDRPlaybook_Test.yml`.

`demisto-sdk generate-test-playbook -i Packs/ExamplePack/Integrations/ExampleIntegration/integration.yml -n Example`
Will create a test playbook in Packs/ExamplePack/TestPlaybooks, with filename `playbook-Example_Test.yml`
