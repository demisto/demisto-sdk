### Generate Test Playbook

Generate Test Playbook from integration/script yml
**Arguments**:
* *-i, --input*
   Specify integration/script yml path (must be a valid yml file)
* *-o, --output*
   Specify output directory (Default: current directory)
* *-n, --name*
   Specify test playbook name
* *-t, --type{integration,script}*
   YAML type (default: integration)

**Examples**:
`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -t integration -o TestPlaybooks`
This will create a test playbook in TestPlaybook folder, with filename `TestXDRPlaybook.yml`.
