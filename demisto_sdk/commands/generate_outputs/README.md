## generate-outputs
Generate outputs for an integration.
Previously `json-to-outputs` and `generate-context` combined.

**Use-Cases**
This command is used to generate context paths automatically from an example file directly into an integration yml file.
Also supports converting JSON format to demisto entry context yaml format.

**Arguments**:
* *-c, --command*
  Command name (e.g. xdr-get-incidents)
* *-j, --json*
  A JSON file path. If not specified then script will wait for user input in the terminal.
* *-p, --prefix*
  Output prefix like Jira.Ticket, VirusTotal.IP
* *-o, --output*
  Output file path, if not specified then will print to stdout
* *-v, --verbose*
  Verbose output - mainly for debugging purposes
* *-int, --interactive*
  If passed, then for each output field will ask user interactively to enter the description. By default is interactive mode is disabled
* *-d, --descriptions*
  A JSON or a path to a JSON file, mapping field names to their descriptions.
* **-i, --input**
  Path of the yml file (ouputs are inserted here in-palce) - used for context from examples.
* **-e, --examples**
  Integrations: path for file containing command examples. Each command should be in a separate line.
* **--insecure**
  Skip certificate validation.
* **-v, --verbose**
  Verbose output - mainly for debugging purposes.
* **--ai**
  AI description generation - \*Experimnetal\* a new way to use GPT-like transformers to generate descriptions from context paths.

**Notes**
* The output of the command will be writen in the input file (in-place).

### Examples
```
demisto-sdk generate-outputs -i Packs/MyPack/Integrations/MyInt/MyInt.yml -e Packs/MyPack/Integrations/MyInt/command_exmaple.txt
```
Before:
```
 commands:
    ...
  name: guardicore-get-incident
  outputs: []
    ...
```
After:
```
commands:
  ...
  name: guardicore-get-incident
  outputs:
  - contextPath: Guardicore.Incident._cls
    description: ''
    type: String
  - contextPath: Guardicore.Incident.affected_assets.ip
    description: ''
    type: String
    ...
```

<br/>`demisto-sdk generate-outputs -c jira-get-ticket -p Jira.Ticket -j path/to/valid.json`
<br/>if valid.json looks like
```json
{
    "id": 100,
    "title": "do something title",
    "created_at": "2019-01-01T00:00:00"
}
```
This command will print to the stdout the following:
```yaml
arguments: []
name: jira-get-ticket
outputs:
- contextPath: Jira.Ticket.id
  description: ''
  type: Number
- contextPath: Jira.Ticket.title
  description: ''
  type: String
- contextPath: Jira.Ticket.created_at
  description: ''
  type: Date
```

#### Experimental: Usage of --ai flag
To use the `--ai` flag you need to register with [ai21.com](https://studio.ai21.com/sign-up) and obtain an API key, replace `KEYHERE` in the examples below with your API key.
Don't share your key with anyone as this can get your account banned. Also don't change or misuse the service:
See the terms and guidelines here: https://studio.ai21.com/terms-of-use https://studio.ai21.com/docs/responsible-use/

##### With JSON-to-Outputs
The `--ai` flag can be used together with the `--json` flag to add descriptions to the generated outputs from the json-to-outputs flow, like so:
`AI21_KEY=KEYHERE demisto-sdk generate-outputs --json test.json -c "test-command" -p "somePrefix" --ai -o out.yml`

##### With Examples
The `--ai` flag can be used together with the `--examples` flag to add descriptions to the generated outputs from the examples flow, like so:
`AI21_KEY=KEYHERE demisto-sdk generate-outputs --examples ./examples_test -i ~/examples.yml --ai`

##### Standalone
You can also use it on a regular integration YAML file like so:
`AI21_KEY=KEYHERE demisto-sdk generate-outputs -i input.yml --ai -o outout.yml`
