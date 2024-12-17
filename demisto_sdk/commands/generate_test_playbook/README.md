## Generate Test Playbook
### Overview

Generate a test playbook from integration/script YAML arguments.

### Options
* **-i, --input**
   Specify integration/script yml path.
* **-o, --output**
   Specify output directory or path. If not specified, and the input is located at `.../Packs/<pack_name>/Integrations`, the output is saved under `.../Packs/<pack_name>/TestPlaybooks`. If no folder in the input hierarchy is named Packs, the output is saved in the current directory.
* **-n, --name**
   Specify test playbook name, the output file name will be `playbook-<name>_Test.yml`
* **--no-outputs**
   Skip generating verification conditions for each output contextPath. Use when you want to decide which outputs to verify and which not
* **-ab, --all-brands**
   Generate a test-playbook which calls commands using integrations of all available brands.
   When not used, the generated playbook calls commands using instances of the provided integration brand.
* **-c, --commands**
   A comma-separated command names to generate playbook tasks for, will ignore the rest of the commands. e.g xdr-get-incidents,xdr-update-incident.
* **-e, --examples**
   For integrations: path for file containing command examples. Each command should be in a separate line.
   For scripts: the script example surrounded by quotes. For example: -e '!ConvertFile entry_id=<entry_id>'.
* **-u, --upload**
   Whether to upload the test playbook after the generation.

**Examples**:

`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -o TestPlaybooks`
Creates a test playbook in TestPlaybook folder, with filename `playbook-TestXDRPlaybook_Test.yml`.

`demisto-sdk generate-test-playbook -i Packs/ExamplePack/Integrations/ExampleIntegration/integration.yml -n Example`
Creates a test playbook in Packs/ExamplePack/TestPlaybooks, with filename `playbook-Example_Test.yml`

`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -o TestPlaybooks -e Integrations/PaloAltoNetworks_XDR/command_examples.txt -c xdr-get-incidents,xdr-update-incident -u`
Creates a test playbook in TestPlaybook folder, with filename `playbook-TestXDRPlaybook_Test.ymll` and generate tasks for only the `xdr-get-incidents,xdr-update-incident` commands of the written in the command_examples file, and also will upload the test playbook to XSOAR.
