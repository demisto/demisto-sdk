### Generate Test Playbook

Generate Test Playbook from integration/script yml
**Arguments**:
* **-i, --input**
   Specify integration/script yml path (must be a valid yml file)
* **-o, --output**
   Specify output directory (Default: current directory)
* **-n, --name**
   Specify test playbook name
* **--no-outputs**
   Skip generating verification conditions for each output contextPath. Use when you want to decide which outputs to verify and which not
* **-v, --verbose**
   Verbose output for debug purposes - shows full exception stack trace

**Examples**:
`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -o TestPlaybooks`
This will create a test playbook in TestPlaybook folder, with filename `TestXDRPlaybook.yml`.
